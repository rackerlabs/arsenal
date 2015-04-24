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

from oslo.config import cfg

from arsenal.common import exception
from arsenal.openstack.common import log
from arsenal.strategy import base as sb

LOG = log.getLogger(__name__)

CONF = cfg.CONF

opts = [
    cfg.FloatOpt('percentage_to_cache',
                 default=0.125,
                 help='The percentage of unprovisioned nodes in each flavor to'
                 'schedule for image caching. Expressed as a floating '
                 'point number between 0 and 1 inclusive, '
                 'where 0 is 0%, 1 is 100%, and 0.5 is 50%.'),
]

sps_group = cfg.OptGroup(name='simple_proportional_strategy',
                              title='Simple Proportional Strategy Options')

CONF = cfg.CONF
CONF.register_group(sps_group)
CONF.register_opts(opts, sps_group)


def build_attribute_set(items, attr_name):
    """Build a set off of a particular attribute of a list of
    objects. Adds 'None' to the set if one or more of the
    objects in items is missing the attribute specified by
    attr_name.
    """
    attribute_set = set()
    for item in items:
        attribute_set.add(getattr(item, attr_name, None))
    return attribute_set


def build_attribute_dict(items, attr_name):
    """Build a dict from a list of items and one of their attributes to make
    querying the collection easier.
    """
    attr_dict = {}
    for item in items:
        attr_dict[getattr(item, attr_name)] = item
    return attr_dict


def nodes_available_for_caching(nodes):
    return filter(lambda node: node.can_cache(), nodes)


def cached_nodes(nodes):
    return filter(lambda node: not node.provisioned and node.cached, nodes)


def unprovisioned_nodes(nodes):
    return filter(lambda node: not node.provisioned, nodes)


def segregate_nodes(nodes, flavors):
    """Segregate nodes by flavor."""
    nodes_by_flavor = {}
    for flavor in flavors:
        nodes_by_flavor[flavor.name] = []

    flavor_names = build_attribute_set(flavors, 'name')

    for node in nodes:
        if node.flavor not in flavor_names:
            LOG.error("Node '%(node)s'with unrecognized flavor '%(flavor)s "
                      "detected. ", {'node': node.uuid, 'flavor': node.flavor})
            next
        nodes_by_flavor[node.flavor].append(node)

    return nodes_by_flavor


def eject_nodes(nodes, image_uuids):
    """Check for cached nodes that have old or
    retired images. Eject them, and mark them as uncached internally.
    """
    ejections = []
    for node in nodes:
        if (node.cached and node.cached_image_uuid not in image_uuids):
            ejections.append(sb.EjectNode(node.node_uuid))
            # This marks the node internally so it's not
            # considered currently cached anymore. The strategy may issue
            # a CacheNode action for the same node, but not necessarily.
            node.cached = False
    return ejections


def cache_nodes(nodes, num_nodes_needed, images):
    available_nodes = nodes_available_for_caching(nodes)
    # If we're not meeting or exceeding
    # our proportion goal, schedule (node, image) pairs to cache
    # randomly until we would meet our proportion goal.
    # TODO(ClifHouck): This selection step can probably be
    # improved.
    nodes_to_cache = []
    random.shuffle(available_nodes)
    for n in range(0, num_nodes_needed):
        node = available_nodes.pop()
        image = random.choice(images)
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
        self.flavor_diff = self.find_flavor_differences(flavors)
        self.log_flavor_differences(self.flavor_diff)
        self.current_flavors = flavors

        # Image differences are important because changed or retired
        # images should be ejected from the cache.
        self.image_diff = self.find_image_differences(images)
        self.log_image_differences(self.image_diff)
        self.current_images = images
        self.current_image_uuids = build_attribute_set(images, 'uuid')

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
        if len(self.current_images) == 0:
            LOG.warning("No images to cache! Are you sure Arsenal is talking "
                        "to Glance properly? No directives issued.")
            return []

        if len(self.current_flavors) == 0:
            LOG.warning("No flavors detected! Are you sure Arsenal is talking "
                        "to Nova properly? No directives issued.")
            return []

        if len(self.current_nodes) == 0:
            LOG.warning("No nodes detected! Are you sure Arsenal is talking "
                        "to Ironic properly? No directives issued.")
            return []

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
        for flavor_name, flavor_nodes in nodes_by_flavor.iteritems():
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

    def find_image_differences(self, new_image_list):
        """Find differences between current image state and
        previous. Did anything change? Which images specifically changed
        their UUIDs? Are some images no longer present at all?

        Returns a dictionary of three attributes: 'new', 'changed', and
        'retired'. Each attribute is a set of image names.
        'new' - Totally new image names.
        'changed' - Images with the same name, but their UUID has changed.
        'retired' - Image name which was previously present, but has since
            disappeared.
        """
        old_image_names = build_attribute_set(self.current_images, 'name')
        new_image_names = build_attribute_set(new_image_list, 'name')

        new_images = new_image_names.difference(old_image_names)
        retired_images = old_image_names.difference(new_image_names)

        # Find 'changed' images
        # This is a bit trickier since we need to check for changing UUIDs.
        same_names = old_image_names.intersection(new_image_names)
        old_image_dict = build_attribute_dict(self.current_images, 'name')
        new_image_dict = build_attribute_dict(new_image_list, 'name')
        changed_images = set()
        for name in same_names:
            new_image_obj = new_image_dict[name]
            old_image_obj = old_image_dict[name]
            # If the UUID of the image has changed, then we know the
            # underlying image has changed somehow.
            if new_image_obj.uuid != old_image_obj.uuid:
                changed_images.add(name)

        return {'new': new_images,
                'changed': changed_images,
                'retired': retired_images}

    def log_image_differences(self, image_differences):
        for image_name in image_differences['new']:
            LOG.info("A new image has been detected. Image name: '%(name)s'",
                     {'name': image_name})
        for image_name in image_differences['changed']:
            LOG.info("A changed image has been detected. "
                     "Image name: '%(name)s'",
                     {'name': image_name})
        for image_name in image_differences['retired']:
            LOG.info("A new image has been detected. Image name: '%(name)s'",
                     {'name': image_name})

    def find_flavor_differences(self, new_flavors):
        """Do a diff on flavors last seen and new set of flavors.
        return differences.

        Assumes that nodes with a particular flavor name are homogeneous, and
        will not change node specifications without an accompaying name change.

        Returns a dictionary with two attributes: 'new', and 'retired'.
        'new' - New flavor names.
        'retired' - Flavor names no longer present.
        All valid keys will map to sets of image names
        as strings.
        """
        previous_flavor_names = build_attribute_set(self.current_flavors,
                                                    'name')
        new_flavor_names = build_attribute_set(new_flavors, 'name')

        totally_new_flavors = new_flavor_names.difference(
            previous_flavor_names)
        retired_flavors = previous_flavor_names.difference(new_flavor_names)
        return {'new': totally_new_flavors, 'retired': retired_flavors}

    def log_flavor_differences(self, flavor_differences):
        for flavor_name in flavor_differences['new']:
            LOG.info("A new flavor has been detected. Flavor name: '%(name)s'",
                     {'name': flavor_name})

        for flavor_name in flavor_differences['retired']:
            LOG.info("A flavor has been retired. Flavor name: '%s(name)'",
                     {'name': flavor_name})
