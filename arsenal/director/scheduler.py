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

from oslo_config import cfg
from oslo_log import log
from oslo_service import periodic_task

from arsenal.common import rate_limiter
from arsenal.common import util
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
    cfg.IntOpt('eject_directive_rate_limit',
               default=0,
               help='Limits how many node-eject directives that can be issued '
                    'by arsenal before triggering a cool-down which prevents '
                    'more ejection directives from being issued until the '
                    'cool-down expires.'),
    cfg.IntOpt('eject_directive_limiting_period',
               default=300,
               help='Determines the amount of time needed to pass before a '
                    'new rate-limit period for ejection directives begins.'),
    cfg.BoolOpt('log_statistics',
                default=True,
                help='When True, Arsenal will log detailed information about '
                     'the state of nodes returned by the configured Scout. '
                     'Including a breakdowns by flavor and images.')
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


def get_configured_rate_limiter(name, rate_limit, limiting_period):
    if rate_limit == 0:
        LOG.info("%s directives will not be rate limited during this run." %
                 (name))
        return None
    LOG.info("%(name)s directives will be rate limited to %(rate_limit)d "
             "every %(seconds)d second(s).", {
                 'name': name,
                 'rate_limit': rate_limit,
                 'seconds': limiting_period})
    return rate_limiter.RateLimiter(
        limit=rate_limit,
        limit_period=limiting_period)


def get_configured_ejection_rate_limiter():
    return get_configured_rate_limiter(
        'Ejection',
        CONF.director.eject_directive_rate_limit,
        CONF.director.eject_directive_limiting_period)


def get_configured_cache_rate_limiter():
    return get_configured_rate_limiter(
        'Cache',
        CONF.director.cache_directive_rate_limit,
        CONF.director.cache_directive_limiting_period)


def rate_limit_directives(rate_limiter, directives, name, identity_func):
        if rate_limiter is not None:
            filtered_directives = filter(identity_func, directives)
            LOG.info("Got %(num)d %(name)s directives from the strategy.",
                     {'num': len(filtered_directives), 'name': name})
            other_directives = filter(lambda d: not identity_func(d),
                                      directives)
            rate_limiter.add_items(filtered_directives)
            rate_limited_directives = rate_limiter.withdraw_items()
            LOG.info("Limited %(name)s directives issued to %(num)d, due to "
                     "rate limiting.",
                     {'num': len(rate_limited_directives), 'name': name})
            directives = rate_limited_directives + other_directives
            # NOTE(ClifHouck): Clearing the items in the rate limiter so
            # that old directives don't stick around. This doesn't
            # affect rate limiting behavior otherwise.
            rate_limiter.clear()
        return directives


class DirectorScheduler(periodic_task.PeriodicTasks):
    """Arsenal Director Scheduler class."""

    def __init__(self):
        super(DirectorScheduler, self).__init__(CONF)
        self.node_data = []
        self.image_data = []
        self.flavor_data = []
        self.strat = sb.get_configured_strategy()
        self.scout = get_configured_scout()
        self.cache_rate_limiter = get_configured_cache_rate_limiter()
        self.eject_rate_limiter = get_configured_ejection_rate_limiter()

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

        return rate_limit_directives(self.cache_rate_limiter,
                                     directives,
                                     'cache',
                                     is_cache_directive)

    def rate_limit_eject_directives(self, directives):
        def is_eject_directive(directive):
            return isinstance(directive, sb.EjectNode)

        return rate_limit_directives(self.eject_rate_limiter,
                                     directives,
                                     'eject',
                                     is_eject_directive)

    @periodic_task.periodic_task(spacing=CONF.director.directive_spacing)
    def issue_directives(self, context):
        # NOTE(ClifHouck): It's really important to have node state be as
        # current as possible. So instead of polling for it, I'm leaving it
        # tied to updating the state of the strategy.
        self.node_data = self.scout.retrieve_node_data()

        self.strat.update_current_state(self.node_data, self.image_data,
                                        self.flavor_data)

        if CONF.director.log_statistics:
            sb.log_overall_node_statistics(self.node_data,
                                           self.flavor_data,
                                           self.image_data)

        directives = self.strat.directives()

        directives = self.rate_limit_cache_directives(directives)
        directives = self.rate_limit_eject_directives(directives)

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
