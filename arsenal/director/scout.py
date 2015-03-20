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

import six


@six.add_metaclass(abc.ABCMeta)
class Scout(object):
    """Scouts data from various sources and massages into nice forms for use
    by Arsenal.
    """

    @abc.abstractmethod
    def retrieve_node_data(self):
        """Get information about nodes to pass to a CachingStrategy object.

        :returns: A list of arsenal.strategy.base.NodeInput objects.
        """
        pass

    @abc.abstractmethod
    def retrieve_flavor_data(self):
        """Get information about flavors to pass to a CachingStrategy object.

        :returns: A list of arsenal.strategy.base.FlavorInput objects.
        """
        pass

    @abc.abstractmethod
    def retrieve_image_data(self):
        """Get information about images to pass to a CachingStrategy object.

        :returns: A list of arsenal.strategy.base.ImageInput objects.
        """
        pass

    @abc.abstractmethod
    def issue_action(self, action):
        """Issue a StrategyAction from arsenal.strategy.base.

        :param action: A StrategyAction object.
        """
        pass
