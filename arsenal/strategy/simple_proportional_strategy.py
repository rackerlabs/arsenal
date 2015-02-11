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

import math
import random

from oslo.config import cfg

from arsenal.openstack.common import log
from arsenal.strategy.base import * 

random.seed()

LOG = log.getLogger(__name__)

CONF = cfg.CONF

def build_attribute_set(items, attr_name):
    """Build a set off of a particular attribute of a list of 
    objects. Adds 'None' to the set if one or more of the
    objects in items is missing the attribute specified by
    attr_name."""
    attribute_set = set()
    for item in items:
        attribute_set.add(getattr(item, attr_name, None))
    return attribute_set

def build_attribute_dict(items, attr_name):
    """ Build a dict from a list of items and one of their attributes to make
    querying the collection easier."""
    attr_dict = {}
    for item in items:
        attr_dict[getattr(item, attr_name)] = item
    return attr_dict

def available_nodes(nodes):
    return filter(lambda node: node.can_cache(), nodes)

class SimpleProportionalStrategy(object):
    def __init__(self, percentage_to_cache = 25):
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
        update_current_state."""

        todo = []
        
        # Segregate nodes by flavor. 
        nodes_by_flavor = {}
        for flavor in self.current_flavors:
            nodes_by_flavor[flavor.name] = []
            for node in self.current_nodes:
                if flavor.is_flavor_node(node):
                    nodes_by_flavor[flavor.name].append(node)

        # For each flavor, check for cached nodes that have old or 
        # retired images. Eject them, and mark them as uncached internally.
        for flavor_name, flavor_nodes in nodes_by_flavor.iteritems():
            for node in flavor_nodes:
                if (node.cached and 
                    node.cached_image_uuid not in self.current_image_uuids):
                        todo.append(EjectNode(node.node_uuid))
                        # This marks the node internally so it's not 
                        # considered currently cached anymore. We may issue
                        # a CacheNode action below for the same node, 
                        # but not necessarily.
                        node.cached = False

        # Once bad cached nodes have been ejected, determine the proportion
        # of truly 'good' cached nodes. 
        for flavor_name, flavor_nodes in nodes_by_flavor.iteritems():
            print "SimpleProportionalStrategy.directives [%s,%d] " % (
                    flavor_name, len(flavor_nodes))
            num_nodes_needed = self.determine_minimum_nodes_needed_to_cache(flavor_nodes)
            nodes_available_for_caching = available_nodes(flavor_nodes)
            print "num_nodes_needed: %d, nodes_available_for_caching: %d" % (
                    num_nodes_needed, len(nodes_available_for_caching))

            for n in range(0, num_nodes_needed):
                # If we're not meeting or exceeding 
                # our proportion goal, schedule (node, image) pairs to cache 
                # randomly until we would meet our proportion goal.
                # TODO(ClifHouck): This selection step can probably be improved.
                rand_node_pick = random.randrange(len(nodes_available_for_caching))
                node = nodes_available_for_caching[rand_node_pick]
                del nodes_available_for_caching[rand_node_pick]
                image = self.current_images[random.randrange(len(self.current_images))]
                todo.append(CacheNode(node.node_uuid, image.uuid))

        return todo

    def determine_minimum_nodes_needed_to_cache(self, nodes):
        num_nodes_cached = len(filter(lambda node: node.cached, nodes))
        num_should_cache = self.determine_number_of_nodes_that_should_cache(nodes)
        num_needed = num_should_cache - num_nodes_cached
        return num_needed

    def determine_number_of_nodes_that_should_cache(self, nodes):
        return int(math.ceil(0.01 * self.percentage_to_cache * len(available_nodes(nodes))))

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

        return { 'new': new_images, 
                 'changed': changed_images,
                 'retired': retired_images }

    def log_image_differences(self, image_differences):
        for image_name in image_differences['new']:
            LOG.info("SimpleProportionalStrategy: A new image has been "
                      "detected. Image name: '%(name)s'", 
                      { 'name': image_name })
        for image_name in image_differences['changed']:
            LOG.info("SimpleProportionalStrategy: A changed image has been "
                      "detected. Image name: '%(name)s'", 
                      { 'name': image_name })
        for image_name in image_differences['retired']:
            LOG.info("SimpleProportionalStrategy: A new image has been "
                      "detected. Image name: '%(name)s'", 
                      { 'name': image_name })

    def find_flavor_differences(self, new_flavors):
        """Do a diff on flavors last seen and new set of flavors.
        return differences.

        Assumes that nodes with a particular flavor name are homogeneous, and
        will not change node specifications without an accompaying name change.

        Returns a dictionary with two attributes: 'new', and 'retired'.
        'new' - New flavor names.
        'retired' - Flavor names no longer present.
        All valid keys will map to sets of image names
        as strings."""
        previous_flavor_names = build_attribute_set(self.current_flavors, 
                                                    'name')
        new_flavor_names = build_attribute_set(new_flavors, 'name')

        totally_new_flavors = new_flavor_names.difference(
                                previous_flavor_names)
        retired_flavors = previous_flavor_names.difference(new_flavor_names)
        return {'new': totally_new_flavors, 'retired': retired_flavors}

    def log_flavor_differences(self, flavor_differences):
        for flavor_name in flavor_differences['new']:
            LOG.info("SimpleProportionalStrategy: A new flavor has been "
                      "detected. Flavor name: '%(name)s'", 
                      { 'name': flavor_name })

        for flavor_name in flavor_differences['retired']:
            LOG.info("SimpleProportionalStrategy: A flavor has been retired. "
                      "Flavor name: '%s(name)'",
                      {'name': flavor_name})

CachingStrategy.register(SimpleProportionalStrategy)
