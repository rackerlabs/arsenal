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

import abc
import collections
import copy
import json
import math

from oslo_config import cfg
from oslo_log import log
import six

from arsenal.common import util

LOG = log.getLogger(__name__)

opts = [
    cfg.StrOpt('module_class',
               default=('simple_proportional_strategy.'
                        'SimpleProportionalStrategy'),
               help='The strategy module to load.'),
    cfg.StrOpt('image_weights_filename',
               help='The name of a file containing a single JSON object. '
                    'The name of each object member is the name of an image '
                    'and the member\'s value ist he corresponding weight as a '
                    'non-negative integer. Arsenal will load the JSON object'
                    'contained within the file and use it whenever '
                    'appropriate to weight strategy decisions on picking '
                    'images to cache.'),
    cfg.IntOpt('default_image_weight',
               default=1,
               help='The integral weight to use if a given image has '
                    'no corresponding entry in image_weights. Default is 1.')
]

strategy_group = cfg.OptGroup(name='strategy',
                              title='Strategy Options')

CONF = cfg.CONF
CONF.register_group(strategy_group)
CONF.register_opts(opts, strategy_group)


def get_configured_strategy():
    # Initialize image weights when the configured strategy is requested.
    # This way we know the configuration is present and ready before trying
    # to read in image weights based on the configured image weight filename.
    init_image_weights()

    loader = util.LoadClass(CONF.strategy.module_class,
                            package_prefix='arsenal.strategy')
    return loader.loaded_class()


class StrategyInput(object):
    """Base class for information destined for CachingStrategy objects."""
    def __init__(self):
        pass


class NodeInput(StrategyInput):
    def __init__(self,
                 node_uuid,
                 flavor,
                 is_provisioned=False,
                 is_cached=False,
                 image_uuid='', ):
        super(NodeInput, self).__init__()
        self.node_uuid = node_uuid
        self.flavor = flavor
        self.provisioned = is_provisioned
        self.cached = is_cached
        self.cached_image_uuid = image_uuid

    def can_cache(self):
        # If the node is not provisioned and not already caching an image,
        # then it is available for caching.
        return (not self.provisioned) and (not self.cached)

    def __str__(self):
        return "[NodeInput]: %s, %s, %s, %s, %s" % (
            self.node_uuid,
            self.flavor,
            "Provisioned" if self.provisioned else "Unprovisioned",
            "Cached" if self.cached else "Not cached",
            self.cached_image_uuid)


class FlavorInput(StrategyInput):
    def __init__(self, name, identity_func):
        super(FlavorInput, self).__init__()
        self.name = name
        self.is_flavor_node = identity_func

    def __str__(self):
        return "[FlavorInput]: %s" % (self.name)


class ImageInput(StrategyInput):
    def __init__(self, name, uuid, checksum):
        super(ImageInput, self).__init__()
        self.name = name
        self.uuid = uuid
        self.checksum = checksum

    def __str__(self):
        return "[ImageInput]: %s, %s, %s" % (self.name,
                                             self.uuid,
                                             self.checksum)


class StrategyAction(object):
    """Base class for actions a CachingStratgy object may take."""
    def __init__(self, format_string="{0}", format_attrs=['name']):
        self.name = self.__class__.__name__
        self.format_string = format_string
        self.format_attrs = format_attrs

    def __str__(self):
        format_list = []
        for attr in self.format_attrs:
            format_list.append(getattr(self, attr))
        return self.format_string.format(*format_list)


class CacheNode(StrategyAction):
    """Contains all the information necessary to cache a specific
    image on a specific node.
    """

    def __init__(self, node_uuid, image_uuid, image_checksum):
        super(CacheNode, self).__init__(
            format_string="{0}: Cache image '{1}' on node '{2}'.",
            format_attrs=['name', 'image_uuid', 'node_uuid'])
        self.node_uuid = node_uuid
        self.image_uuid = image_uuid
        self.image_checksum = image_checksum


class EjectNode(StrategyAction):
    def __init__(self, node_uuid):
        super(EjectNode, self).__init__(
            format_string="{0}: Eject node '{1}' from cache.",
            format_attrs=['name', 'node_uuid'])
        self.node_uuid = node_uuid


@six.add_metaclass(abc.ABCMeta)
class CachingStrategy(object):
    """Base object for objects that will implement a caching strategy for
    Arsenal.
    """

    @abc.abstractmethod
    def update_current_state(self, nodes, images, flavors):
        """update_current_state should be called periodically to allow the
        strategy to see what the current state of nodes, images, and flavors
        are in the system.
        """
        pass

    @abc.abstractmethod
    def directives(self):
        """directives will return a list of StrategyActionsArsenal should take
        to fulfill this object's strategy, based on its view of the current
        system state.
        """
        pass


def build_node_statistics(nodes, images):
    """Build a dictionary of cache statistics about a group of nodes."""
    # Generic statistics applicable to all groups of nodes.
    node_statistics = {
        'provisioned': len(filter(lambda n: n.provisioned, nodes)),
        'not provisioned': len(filter(lambda n: not n.provisioned, nodes)),
        'available (not cached)': len(filter(lambda n: n.can_cache(), nodes)),
        'cached (includes \'caching\')':
            len(filter(lambda n: n.cached and not n.provisioned, nodes)),
        'total': len(nodes),
        'images': collections.defaultdict(lambda: 0)
    }

    image_names_by_uuid = {image.uuid: image.name for image in images}

    # Build statistics around which images are cached.
    for node in nodes:
        if (node.cached and
                not node.provisioned and
                node.cached_image_uuid is not None):
            # If we don't know the name of the image, just return the UUID.
            image_name = image_names_by_uuid.get(node.cached_image_uuid,
                                                 node.cached_image_uuid)
            node_statistics['images'][image_name] += 1

    return node_statistics


def log_node_statisitics(built_statistics):
    """Log statistics generated by build_node_statistics."""
    LOG.info("General statistics:")
    for key, value in six.iteritems(built_statistics):
        if key != "images":
            LOG.info("    %(key)s: %(value)d", {'key': key, 'value': value})

    LOG.info("Breakdown of cached nodes by image (omits images with count 0):")
    for image_name, image_count in six.iteritems(built_statistics['images']):
        if image_count != 0:
            LOG.info("    %(name)s: %(num)d",
                     {'name': image_name, 'num': image_count})


def log_overall_node_statistics(nodes, flavors, images):
    """Build & Log statistics about nodes, both overall and by flavor."""
    # We want stats about the all nodes.
    overall_statistics = build_node_statistics(nodes, images)
    LOG.info("Overall node statistics.")
    log_node_statisitics(overall_statistics)

    # As well as those divided by flavor.
    flavor_stats = {}
    for flavor in flavors:
        flavor_nodes = filter(lambda n: n.flavor == flavor.name, nodes)
        flavor_stats[flavor.name] = build_node_statistics(flavor_nodes,
                                                          images)
        LOG.info("Statistics for '%(name)s' flavor.", {'name': flavor.name})
        log_node_statisitics(flavor_stats[flavor.name])


def find_image_differences(current_image_list, new_image_list):
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
    old_image_names = build_attribute_set(current_image_list, 'name')
    new_image_names = build_attribute_set(new_image_list, 'name')

    new_images = new_image_names.difference(old_image_names)
    retired_images = old_image_names.difference(new_image_names)

    # Find 'changed' images
    # This is a bit trickier since we need to check for changing UUIDs.
    same_names = old_image_names.intersection(new_image_names)
    old_image_dict = build_attribute_dict(current_image_list, 'name')
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


def log_image_differences(image_differences):
    for image_name in image_differences['new']:
        LOG.info("A new image has been detected. Image name: '%(name)s'",
                 {'name': image_name})
    for image_name in image_differences['changed']:
        LOG.info("A changed image has been detected. "
                 "Image name: '%(name)s'",
                 {'name': image_name})
    for image_name in image_differences['retired']:
        LOG.info("A retired image has been detected. Image name: '%(name)s'",
                 {'name': image_name})


def find_flavor_differences(current_flavors, new_flavors):
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
    previous_flavor_names = build_attribute_set(current_flavors,
                                                'name')
    new_flavor_names = build_attribute_set(new_flavors, 'name')

    totally_new_flavors = new_flavor_names.difference(
        previous_flavor_names)
    retired_flavors = previous_flavor_names.difference(new_flavor_names)
    return {'new': totally_new_flavors, 'retired': retired_flavors}


def log_flavor_differences(flavor_differences):
    for flavor_name in flavor_differences['new']:
        LOG.info("A new flavor has been detected. Flavor name: '%(name)s'",
                 {'name': flavor_name})

    for flavor_name in flavor_differences['retired']:
        LOG.info("A flavor has been retired. Flavor name: '%s(name)'",
                 {'name': flavor_name})


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


def _load_image_weights_file(reload_file=False):
    filename = CONF.strategy.image_weights_filename

    if filename is None:
        LOG.warning("Configuration option strategy.image_weights_filename is "
                    "not specified, every image will receive the default "
                    "image weight.")
        return

    if _load_image_weights_file.loaded and not reload_file:
        LOG.warning("The image weight file has already been loaded. Refusing "
                    "to reload unless the reload_file argument is True.")
        return

    try:
        with open(filename, 'r') as infile:
            _load_image_weights_file.image_weights = json.load(infile)
            _load_image_weights_file.loaded = True
        LOG.info("Loaded image weights from '%s'." % (filename))
        LOG.info("Image weights as follows:")
        for image_name, weight in (
                six.iteritems(_load_image_weights_file.image_weights)):
            LOG.info("%(image_name)s: %(weight)d" % {'image_name': image_name,
                                                     'weight': weight})
    except Exception as e:
        LOG.exception("Caught an exception when trying to load "
                      "'%(filename)s'. All weights will revert to the "
                      "default image weight. Exception message: "
                      "%(message)s" % {'filename': filename, 'message': e})
        _load_image_weights_file.image_weights = {}
        _load_image_weights_file.loaded = False

_load_image_weights_file.loaded = False
_load_image_weights_file.image_weights = {}


def init_image_weights():
    LOG.info("Initializing image weights for strategy use.")
    _load_image_weights_file()


def get_image_weights(image_names):
    """Return a dictionary of requested image names to weights."""
    default_weight = CONF.strategy.default_image_weight
    weights_by_name = {}
    for name in image_names:
        weight = _load_image_weights_file.image_weights.get(name)
        if weight is None:
            weight = default_weight
        weights_by_name[name] = weight
    return weights_by_name


def _determine_image_distribution(nodes):
    """Finds the current distribution of cached images across available nodes.

    Returns a dictionary where the keys are image uuids and the values are
    the integral frequency of their occurance.
    """
    cached_images = [node.cached_image_uuid for node in nodes
                     if (node.cached_image_uuid is not None and
                         node.cached and
                         not node.provisioned)]
    current_image_distribution = collections.defaultdict(lambda: 0)
    for image_uuid in cached_images:
        current_image_distribution[image_uuid] += 1
    return current_image_distribution


def _pick_images(images,
                 distribution_difference_dict,
                 num_images,
                 picker_func,
                 distribution_mutator_func):
    """Function to abstract picking images with a distribution differential

    picker_func should return a selection from distribution_difference_dict.

    distribution_mutator_func should mutate either the returned pair or the
    overall difference dictionary in order to make the next proper
    selection.
    """

    # Avoid side effects propogating outside the function.
    difference_dict = copy.deepcopy(distribution_difference_dict)

    picked_images = []
    for n in range(0, num_images):
        most_needed_image_pair = picker_func(difference_dict)
        # Adds the most 'needed' image, based on picker_func's preference.
        picked_images.append(most_needed_image_pair[0])
        # Update the distribution to reflect the selected image being
        # scheduled to cache onto a node.
        distribution_mutator_func(most_needed_image_pair, difference_dict)

    return picked_images


def _get_scaled_weights(images, scale_factor):
    # Get weighted image information from the strategy base.
    weights_by_name = get_image_weights([image.name for image in images])

    # NOTE(ClifHouck): The scaled weights will not be integers, but that's OK.
    # This is more accurate than forcing the scaled weights to integral
    # factors.
    scaled_weights = {
        image.name: scale_factor * weights_by_name[image.name]
        for image in images
    }

    return scaled_weights


def _get_scale_factor_for_caching_nodes(num_images_to_cache,
                                        images,
                                        nodes):
    # Get weighted image information from the strategy base.
    weights_by_name = get_image_weights([image.name for image in images])

    # Scale the desired distribution to match the number of nodes to be in
    # the cache.
    weight_sum = sum([weights_by_name[image.name] for image in images])

    num_cached_nodes = len([node for node in nodes if
                            node.cached and not node.provisioned])
    total_desired_cached = num_cached_nodes + num_images_to_cache

    scale_factor = 1
    if weight_sum != 0:
        scale_factor = total_desired_cached / weight_sum

    return scale_factor


def _get_named_image_distribution(images, nodes):
    # Get the distribution by image uuid and then translate uuids to names.
    uuid_distribution = _determine_image_distribution(nodes)
    image_uuids_to_names = {image.uuid: image.name for image in images}

    named_distribution = collections.defaultdict(lambda: 0)
    for uuid, frequency in six.iteritems(uuid_distribution):
        named_distribution[image_uuids_to_names[uuid]] = frequency

    return named_distribution


def choose_weighted_images_forced_distribution(num_images, images, nodes):
    """Returns a list of images to cache

    Enforces the distribution of images to match the weighted distribution as
    closely as possible.  Factors in the current distribution of images cached
    across nodes.

    It is important to note that there may be circumstances which prevent this
    function from attaining the desired ideal distribution, but the function
    will always try its best to reach the desired distribution based on the
    specified weights.

    num_images - the number (integer) of images to choose to cache
    images - a list of to ImageInputs consider for caching
    nodes - a list of NodeInputs to use for determining which images
        need to be cached the most
    """
    named_distribution = _get_named_image_distribution(images, nodes)

    # Take the difference of the desired distribution with the current
    # one.
    scaled_weights = _get_scaled_weights(
        images, _get_scale_factor_for_caching_nodes(num_images, images, nodes))
    distribution_difference = [
        [image, (scaled_weights[image.name] - named_distribution[image.name])]
        for image in images
    ]

    def decrement_distribution(distribution_pair, diff_dict):
        distribution_pair[1] -= 1

    return _pick_images(
        images, distribution_difference, num_images,
        picker_func=lambda diff: max(diff, key=lambda pair: pair[1]),
        distribution_mutator_func=decrement_distribution)


def image_weight_guided_ejection(images, nodes):
    """Using the image weights as a guide, determine which images to eject.

    The idea is to figure out which images (by proxy of the node they are
    cached to) to eject in order to best fulfill the goal of reaching the
    desired distribution determined by the configured image weights.

    Returns a list of images in order of which to eject first. That is, to best
    reach the desired distribution, eject a node with the image
    returned_images[0] first, then eject a node with the image
    returned_images[1] second, and so on until the list is exhausted.

    This way the consumer of image_weight_guided_ejection can decide to
    eject just the first n nodes (corresponding to the selected images)
    from the returned listvalue, and have a reasonable expectation
    that will do the most good in trying to reach the desired ideal
    distribution determined by the configured image weights.

    Note that this will return the same number of images as the number of
    cached nodes found in 'nodes'.
    """
    # Determine the current distribution of images across nodes.
    named_distribution = _get_named_image_distribution(images, nodes)

    # Find the difference between the ideal distribution in the cache,
    # versus the reality.
    scaled_weights = _get_scaled_weights(
        images, _get_scale_factor_for_caching_nodes(0, images, nodes))
    distribution_difference = [
        [image, (scaled_weights[image.name] - named_distribution[image.name])]
        for image in images
    ]

    # Only those that are cached too much.
    images_cached_too_much = filter(lambda pair: pair[1] < 0,
                                    distribution_difference)

    # This computes the approximate number of nodes we should eject to
    # best reach the desired distribution.
    max_to_eject = int(math.floor(
        abs(sum([pair[1] for pair in images_cached_too_much]))))

    # Pick images to eject based on how far above the distribution they
    # appear in the current cache. In this case, images cached more than they
    # should be will have negative values in the distribution difference.
    def increment_distribution(distribution_pair, diff_dict):
        distribution_pair[1] += 1

    return _pick_images(
        images, images_cached_too_much, max_to_eject,
        picker_func=lambda diff: min(diff, key=lambda pair: pair[1]),
        distribution_mutator_func=increment_distribution)
