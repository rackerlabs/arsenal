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

from __future__ import division

import math
import random

from oslo_config import cfg
from oslo_log import log
import six

from arsenal.common import exception
from arsenal.strategy import base as sb

LOG = log.getLogger(__name__)

CONF = cfg.CONF

opts = [
    cfg.FloatOpt('percentage_to_cache',
                 default=0.125,
                 help='The percentage of unprovisioned nodes in each flavor to'
                 'schedule for image caching. Expressed as a floating '
                 'point number between 0 and 1 inclusive, '
                 'where 0 is 0%, 1 is 100%, and 0.5 is 50%.')
]

sps_group = cfg.OptGroup(name='simple_proportional_strategy',
                              title='Simple Proportional Strategy Options')

CONF = cfg.CONF
CONF.register_group(sps_group)
CONF.register_opts(opts, sps_group)


def nodes_available_for_caching(nodes):
    return list(filter(lambda node: node.can_cache(), nodes))


def cached_nodes(nodes):
    return list(filter(lambda node: not node.provisioned and node.cached,
                       nodes))


def unprovisioned_nodes(nodes):
    return list(filter(lambda node: not node.provisioned, nodes))


def segregate_nodes(nodes, flavors):
    """Segregate nodes by flavor."""
    nodes_by_flavor = {}
    for flavor in flavors:
        nodes_by_flavor[flavor.name] = []

    flavor_names = sb.build_attribute_set(flavors, 'name')

    for node in nodes:
        if node.flavor not in flavor_names:
            LOG.error("Node '%(node)s'with unrecognized flavor '%(flavor)s "
                      "detected. ", {'node': node.node_uuid,
                                     'flavor': node.flavor})
            continue
        nodes_by_flavor[node.flavor].append(node)

    return nodes_by_flavor


def eject_nodes(nodes, image_uuids):
    """Check for cached nodes that have old or
    retired images. Eject them, and mark them as provisioned internally.
    """
    ejections = []
    for node in nodes:
        if (not node.provisioned and
                node.cached and
                node.cached_image_uuid not in image_uuids):
            ejections.append(sb.EjectNode(node.node_uuid))
            # This marks the node internally so it can't be considered for
            # caching immediately.
            node.provisioned = True
    return ejections


def cache_nodes(nodes, num_nodes_needed, images):
    available_nodes = nodes_available_for_caching(nodes)

    # Choose the images to cache in advance, based on how many nodes we should
    # use for caching.
    chosen_images = sb.choose_weighted_images_forced_distribution(
        num_nodes_needed, images, nodes)

    # If we're not meeting or exceeding our proportion goal,
    # schedule (node, image) pairs to cache until we would meet
    # our proportion goal.
    nodes_to_cache = []
    random.shuffle(available_nodes)
    for n in range(0, num_nodes_needed):
        node = available_nodes.pop()
        image = chosen_images.pop()
        nodes_to_cache.append(sb.CacheNode(node.node_uuid,
                                           image.uuid,
                                           image.checksum))
    return nodes_to_cache


def how_many_nodes_should_cache(nodes, percentage_to_cache):
    should_cache = int(math.floor(percentage_to_cache * len(
        unprovisioned_nodes(nodes)))) - len(cached_nodes(nodes))
    if should_cache < 0:
        should_cache = 0
    LOG.debug("Should cache %(should_cache)d node(s), based on number "
              "of unprovisioned nodes: %(unpro)d, number of cached "
              "nodes %(cached)d, and the percentage of unprovisioned nodes "
              "to cache: %(to_cache_percentage)f",
              {'should_cache': should_cache,
               'unpro': len(unprovisioned_nodes(nodes)),
               'cached': len(cached_nodes(nodes)),
               'to_cache_percentage': percentage_to_cache})
    return should_cache


class InvalidPercentageError(exception.ArsenalException):
    msg_fmt = ("An invalid percentage was specified. Percentages should be "
               "less than or equal to 1, and greater than or equal to 0. "
               "Got '%(percentage)f'.")


class SimpleProportionalStrategy(object):
    def __init__(self):
        percentage_to_cache = (
            CONF.simple_proportional_strategy.percentage_to_cache)
        # Clamp the percentage to reasonable values.
        if percentage_to_cache < 0 or percentage_to_cache > 1:
            raise InvalidPercentageError(percentage=percentage_to_cache)

        LOG.info("Initializing with proportional goal of %(goal)f",
                 {'goal': percentage_to_cache})

        self.percentage_to_cache = percentage_to_cache
        self.current_flavors = []
        self.current_images = []
        self.current_nodes = []

    def update_current_state(self, nodes, images, flavors):
        # For now, flavors should remain static.
        # In the future we'll handle changing flavor profiles if needed,
        # but it seems unlikely that flavors will change often enough.
        self.flavor_diff = sb.find_flavor_differences(self.current_flavors,
                                                      flavors)
        sb.log_flavor_differences(self.flavor_diff)
        self.current_flavors = flavors

        # Image differences are important because changed or retired
        # images should be ejected from the cache.
        self.image_diff = sb.find_image_differences(self.current_images,
                                                    images)
        sb.log_image_differences(self.image_diff)
        self.current_images = images
        self.current_image_uuids = sb.build_attribute_set(images, 'uuid')

        # We don't compare old node state versus new, because that would be
        # a relatively large and complicated task. Instead, we only rely on
        # the current state of nodes to inform ourselves whether we're meeting
        # our stated goals or not.
        self.current_nodes = nodes

    def directives(self):
        """Return a list actions that should be taken by Arsenal in order to
        fulfill the strategy implemented by this object. Bases
        decision-making on data made available to it by Arsenal through
        update_current_state.
        """
        todo = []

        # Eject nodes.
        todo.extend(
            eject_nodes(
                self.current_nodes,
                map(lambda image: image.uuid, self.current_images)))

        # Once bad cached nodes have been ejected, determine the proportion
        # of truly 'good' cached nodes.
        nodes_by_flavor = segregate_nodes(self.current_nodes,
                                          self.current_flavors)
        for flavor_name, flavor_nodes in six.iteritems(nodes_by_flavor):
            num_nodes_needed = how_many_nodes_should_cache(
                flavor_nodes, self.percentage_to_cache)
            LOG.debug("Need to cache %(needed)d node(s) for flavor "
                      "'%(flavor)s'.",
                      {'needed': num_nodes_needed, 'flavor': flavor_name})
            nodes_to_cache = cache_nodes(flavor_nodes, num_nodes_needed,
                                         self.current_images)
            todo.extend(nodes_to_cache)

        LOG.debug("Issuing %(num)d directives(s).", {'num': len(todo)})

        return todo
