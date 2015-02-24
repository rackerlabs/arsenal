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

import abc
import importlib

from oslo.config import cfg
import six

from arsenal.common import exception


opts = [
    cfg.StrOpt('module',
               default='arsenal.strategy.simple_proportional_strategy',
               help='The strategy module to load.'),
    cfg.StrOpt('strategy_class',
               default='SimpleProportionalStrategy',
               help='The strategy class to instantiate and use to direct '
                    'Arsenal\'s caching operations.')
]

strategy_group = cfg.OptGroup(name='strategy',
                              title='Strategy Options')

CONF = cfg.CONF
CONF.register_group(strategy_group)
CONF.register_opts(opts, strategy_group)


class ImportStrategyModuleException(exception.ArsenalException):
    msg_fmt = "Couldn't import strategy module '%(module_name)s'"


class CreateStrategyObjectException(exception.ArsenalException):
    msg_fmt = "Couldn't create the specified strategy object'%(class_name)s'"


def get_configured_strategy():
    """Get the configured strategy object. Loads the strategy module and
    instantiates the configured class if it hasn't been done already.

    Raises ImportStrategyModuleException if the configured strategy module
    fails to import. Raises CreateStrategyObjectException if the configured
    class fails to insantiate.
    """
    if get_configured_strategy.strat_module is None:
        try:
            get_configured_strategy.strat_module = (
                importlib.import_module(CONF.strategy.module,
                                        package='arsenal.strategy'))
        except ImportError:
            raise ImportStrategyModuleException(
                module_name=CONF.strategy.module)

    if get_configured_strategy.strat_obj is None:
        try:
            configured_class = getattr(get_configured_strategy.strat_module,
                                       CONF.strategy.strategy_class)
            get_configured_strategy.strat_obj = configured_class()
        except AttributeError:
            raise CreateStrategyObjectException(
                class_name=CONF.strategy.strategy_class)

    return get_configured_strategy.strat_obj
get_configured_strategy.strat_module = None
get_configured_strategy.strat_obj = None


class StrategyInput(object):
    """Base class for information destined for CachingStrategy objects."""
    def __init__(self):
        pass


class NodeInput(StrategyInput):
    def __init__(self, node_uuid, is_provisioned=False, is_cached=False,
                 image_uuid=''):
        super(NodeInput, self).__init__()
        self.node_uuid = node_uuid
        self.provisioned = is_provisioned
        self.cached = is_cached
        self.cached_image_uuid = image_uuid

    def can_cache(self):
        # If the node is not provisioned and not already caching an image,
        # then it is available for caching.
        return (not self.provisioned) and (not self.cached)

    def __str__(self):
        return "[NodeInput]: %s, %s, %s, %s" % (
            self.node_uuid,
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
    def __init__(self, name, uuid):
        super(ImageInput, self).__init__()
        self.name = name
        self.uuid = uuid

    def __str__(self):
        return "[ImageInput]: %s, %s" % (self.name, self.uuid)


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

    def __init__(self, node_uuid, image_uuid):
        super(CacheNode, self).__init__(
            format_string="{0}: Cache image '{1}' on node '{2}'.",
            format_attrs=['name', 'image_uuid', 'node_uuid'])
        self.node_uuid = node_uuid
        self.image_uuid = image_uuid


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
        """directives will return a list of simple actions Arsenal should take
        to fulfill this object's strategy, based on its view of the current
        system state.
        """
        pass
