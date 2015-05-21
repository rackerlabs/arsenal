# -*- encoding: utf-8 -*-
#
# Copyright 2015 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo.config import cfg

from arsenal.common import rate_limiter
from arsenal.common import util
from arsenal.openstack.common import log
from arsenal.openstack.common import periodic_task
from arsenal.strategy import base as sb

LOG = log.getLogger(__name__)

CONF = cfg.CONF

opts = [
    cfg.StrOpt('scout',
               help='The scout modulename and class name to load in the '
                    'director. Should follow the format: '
                    'module_name.ClassName'),
    cfg.IntOpt('poll_spacing',
               default=120,
               help='How long to wait, in seconds, between polling various '
                    'sources (Ironic, Nova, Glance, etc.) for data.'),
    cfg.IntOpt('directive_spacing',
               default=120,
               help='How long to wait, in seconds, between issuing new '
                    'directives from the configured strategy object.'),
    cfg.BoolOpt('dry_run',
                default=False,
                help='When true, prevents Arsenal from issuing directives. '
                     'Useful for debugging configuration or strategy issues '
                     'in a real environment, without affecting outside '
                     'services.'),
    cfg.IntOpt('cache_directive_rate_limit',
               default=0,
               help='Limits how many cache directives that can be issued by'
                    'arsenal before triggering a cool-down which prevents more'
                    'cache directives from being issued until the cool-down '
                    'expires.'),
    cfg.IntOpt('cache_directive_limiting_period',
               default=300,
               help='Determines the amount of time needed to pass before a '
                    'new rate-limit period for cache directives begins.'),
]

director_group = cfg.OptGroup(name='director',
                              title='Configuration for Arsenal\'s '
                                    'DirectorScheduler.')

CONF = cfg.CONF
CONF.register_group(director_group)
CONF.register_opts(opts, director_group)


def get_configured_scout():
    loader = util.LoadClass(CONF.director.scout,
                            package_prefix='arsenal.director')
    return loader.loaded_class()


def get_configured_rate_limiter():
    if CONF.director.cache_directive_rate_limit == 0:
        LOG.info("Cache directives will not be rate limited during this run.")
        return None
    LOG.info("Cache directives will be rate limited to %(rate_limit)d "
             "every %(seconds)d second(s).", {
                 'rate_limit': CONF.director.cache_directive_rate_limit,
                 'seconds': CONF.director.cache_directive_limiting_period})
    return rate_limiter.RateLimiter(
        limit=CONF.director.cache_directive_rate_limit,
        limit_period=CONF.director.cache_directive_limiting_period)


class DirectorScheduler(periodic_task.PeriodicTasks):
    """Arsenal Director Scheduler class."""

    def __init__(self):
        super(DirectorScheduler, self).__init__()
        self.node_data = []
        self.image_data = []
        self.flavor_data = []
        self.strat = sb.get_configured_strategy()
        self.scout = get_configured_scout()
        self.cache_directive_rate_limiter = get_configured_rate_limiter()

    def periodic_tasks(self, context, raise_on_error=False):
        return self.run_periodic_tasks(context, raise_on_error)

    @periodic_task.periodic_task(run_immediately=True,
                                 spacing=CONF.director.poll_spacing)
    def poll_for_flavor_data(self, context):
        self.flavor_data = self.scout.retrieve_flavor_data()

    @periodic_task.periodic_task(run_immediately=True,
                                 spacing=CONF.director.poll_spacing)
    def poll_for_image_data(self, context):
        self.image_data = self.scout.retrieve_image_data()

    def rate_limit_cache_directives(self, directives):
        def is_cache_directive(directive):
            return isinstance(directive, sb.CacheNode)

        if self.cache_directive_rate_limiter is not None:
            cache_directives = filter(is_cache_directive, directives)
            other_directives = filter(lambda d: not is_cache_directive(d),
                                      directives)
            self.cache_directive_rate_limiter.add_items(cache_directives)
            rl_cache_dirs = self.cache_directive_rate_limiter.withdraw_items()
            LOG.info("Limited cache directives issued to %(num)d, due to "
                     "rate limiting.", {'num', len(rl_cache_dirs)})
            directives = rl_cache_dirs + other_directives
            # NOTE(ClifHouck): Clearing the items in the rate limiter so
            # that old cache directives don't stick around. This doesn't
            # affect rate limiting behavior otherwise.
            self.cache_directive_rate_limiter.clear()
        return directives

    @periodic_task.periodic_task(spacing=CONF.director.directive_spacing)
    def issue_directives(self, context):
        # NOTE(ClifHouck): It's really important to have node state be as
        # current as possible. So instead of polling for it, I'm leaving it
        # tied to updating the state of the strategy.
        self.node_data = self.scout.retrieve_node_data()
        self.strat.update_current_state(self.node_data, self.image_data,
                                        self.flavor_data)
        directives = self.strat.directives()

        directives = self.rate_limit_cache_directives(directives)

        if CONF.director.dry_run:
            LOG.info("Director is in dry-run mode. No directives will be "
                     "issued during this run.")
            LOG.info("Got %(num)s directive(s) from the configured strategy.",
                     {'num': len(directives)})
            for directive in directives:
                LOG.info(str(directive))
            return
        else:
            LOG.info("Issuing all directives through configured scout.")
            map(self.scout.issue_action, directives)
