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

import arsenal.external.ironic_client_wrapper as icw
import arsenal.external.nova_client_wrapper as ncw
from arsenal.strategy import base as sb


def is_node_provisioned(ironic_node):
    # FIXME(ClifHouck): This probably needs revising.
    # The node is considered provisioned if the state is not null,
    # and either has an instance UUID or is in maintenance mode.
    return (ironic_node.provision_state is not None and
            (getattr(ironic_node, 'instance_uuid', None) is not None or
             not ironic_node.maintenance))


def is_node_cached(ironic_node):
    # TODO(ClifHouck)
    return False


def get_node_cached_image_uuid(ironic_node):
    # TODO(ClifHouck)
    return ''


def convert_node(ironic_node):
    return sb.NodeInput(ironic_node.uuid,
                        is_node_provisioned(ironic_node),
                        is_node_cached(ironic_node),
                        get_node_cached_image_uuid(ironic_node))


def convert_image(nova_image):
    return sb.ImageInput(nova_image.name, nova_image.id)


def convert_flavor(nova_flavor):
    # TODO(ClifHouck): How do I get the identity function bound to this
    # flavor?
    return sb.FlavorInput(nova_flavor.name, None)


class Scout(object):
    """Scouts data from various sources and massages into nice forms for use
    by Arsenal.
    """
    def __init__(self):
        self.ironic_client = icw.IronicClientWrapper()
        self.nova_client = ncw.NovaClientWrapper()

    def retrieve_node_data(self):
        """Get information about nodes from Ironic to pass to an Arsenal
        CachingStrategy object.
        """
        # TODO(ClifHouck): Check for maximum node list limits?
        node_list = self.ironic_client.call("node.list", limit=0)

        # Massage into input suitable for strategies.
        return map(convert_node, node_list)

    def retrieve_flavor_data(self):
        # TODO(ClifHouck): Check for maximum flavor list limits?
        flavor_list = self.nova_client.call("flavors.list")
        return map(convert_flavor, flavor_list)

    def retrieve_image_data(self):
        # TODO(ClifHouck): Check for maximum image list limits?
        image_list = self.nova_client.call("images.list")
        return map(convert_image, image_list)
