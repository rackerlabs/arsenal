# -*- encoding: utf-8 -*-
#
# Copyright 2016 Rackspace
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

import copy

from oslo_config import cfg
from oslo_log import log

from arsenal.common import exception as exc
from arsenal.director import scout
import arsenal.external.glance_client_wrapper as gcw
import arsenal.external.ironic_client_wrapper as icw
import arsenal.external.nova_client_wrapper as ncw
from arsenal.strategy import base as sb


LOG = log.getLogger(__name__)

CONF = cfg.CONF


def is_node_provisioned(ironic_node):
    # NOTE(ClifHouck): In some versions of the Ironic API, the node's
    # provision_state is None when the node is not provisioned.
    # We treat these nodes as having aprovision_state of available.
    provision_state = ironic_node.provision_state or 'available'
    # A node is 'provisioned' for arsenal's purposes if the node is not
    # available or the node is in maintenance mode.
    return provision_state != 'available' or ironic_node.maintenance


def is_node_cached(ironic_node):
    cache_status = ironic_node.driver_info.get('cache_status')
    if cache_status is None or cache_status == 'failed':
        return False
    else:
        return True


def get_node_cached_image_uuid(ironic_node):
    return ironic_node.driver_info.get('cache_image_id') or ''


def resolve_flavor(ironic_node, known_flavors=None):
    """Attempt to identify the flavor of an ironic node.

    :param: ironic_node - An ironic node data structure which represents
        an ironic node as returned by the 'nodes.list' request to Ironic.
    :param: known_flavors - A dictionary mapping flavor names (strings)
        to identity functions. This allows a user to supply their own
        identification functions. Each function will be fed one
        argument: The ironic_node param listed above. The 'first'
        identity function that returns True will identify the flavor
        of the node.
    :returns: flavor_name - The identified flavor name or None.
    """
    # Try to resolve the flavor using ironic_node.extra
    extra = getattr(ironic_node, 'extra', None)
    flavor_extra = None
    if extra is not None:
        flavor_extra = extra.get('flavor', None)

    if flavor_extra is not None:
        return flavor_extra

    # Otherwise use known flavor hueristics to try identifying the flavor.
    if known_flavors is not None:
        for flavor, ident_func in known_flavors.iteritems():
            if ident_func(ironic_node):
                return flavor

    # We failed...
    return None


def convert_ironic_node(ironic_node, known_flavors=None):
    flavor_name = resolve_flavor(ironic_node, known_flavors)

    if flavor_name is None:
        LOG.error("Unable to identify flavor of node '%(node)s'",
                  {'node': ironic_node.uuid})
        return None

    return sb.NodeInput(ironic_node.uuid,
                        flavor_name,
                        is_node_provisioned(ironic_node),
                        is_node_cached(ironic_node),
                        get_node_cached_image_uuid(ironic_node))


def convert_glance_image(glance_image):
    return sb.ImageInput(glance_image.get('name'),
                         glance_image.get('id'),
                         glance_image.get('checksum'))


def convert_nova_flavor(nova_flavor, known_flavors):
    return sb.FlavorInput(nova_flavor.id,
                          known_flavors.get(nova_flavor.id))


class OpenstackScout(scout.Scout):
    """Generic scout to use against an openstack deployment.

       Talks to Ironic for node information and issuing strategy actions.
       Talks to Nova for flavor information.
       Talks to Glance for image information.
    """
    def __init__(self, flavor_filter, image_filter, glance_auth_token_func,
                 known_flavors):
        """Constructs an OpenstackScout object.

        :param: flavor_filter - A function that should return True for
            flavors which the scout should include when
            returning information bound for Strategy objects. Returning
            False will cause the scout to ignore nodes of that flavor.
        :param: image_filter - A functiion which should return True for images
            to use for caching, and False for those to ignore. The function
            will accept a single argument of a Python'd JSON flavor as
            returned by a Nova flavor-list request.
        :param: glance_auth_token_func - A function which will return an
            authorization token for the Glance client to use for authenticating
            requests. It should accept the following keyword arguments:
                auth_url - The url to request the token from.
                username - Username for token request.
                password - Password for token request.
            See the GlanceClientWrapper class for more information about which
            keyword arguments will be sent to this function. This function
            could potentially ignore the keyword arguments if the function is
            able to authorize through other means.
        :param: known_flavors - A dictionary mapping flavor names (strings)
            to identity functions. This allows a user to supply their own
            identification functions. Each function will be fed one
            argument: The ironic_node param listed above. The 'first'
            identity function that returns True will identify the flavor
            of the node.
        """
        self.flavor_filter = flavor_filter
        self.image_filter = image_filter
        self.ironic_client = icw.IronicClientWrapper()
        self.nova_client = ncw.NovaClientWrapper()
        self.glance_client = gcw.GlanceClientWrapper(glance_auth_token_func)
        self.glance_data = []
        self.known_flavors = copy.deepcopy(known_flavors)

        def curried_convert_ironic_node(ironic_node):
            return convert_ironic_node(ironic_node, self.known_flavors)

        self.curried_convert_ironic_node = curried_convert_ironic_node

        def curried_convert_nova_flavor(nova_flavor):
            return convert_nova_flavor(nova_flavor, self.known_flavors)

        self.curried_convert_nova_flavor = curried_convert_nova_flavor

    def retrieve_node_data(self):
        """Get information about nodes to pass to a CachingStrategy object.

        """
        node_list = self.ironic_client.call("node.list", limit=0, detail=True)
        return filter(lambda n: n is not None,
                      map(self.curried_convert_ironic_node, node_list))

    def retrieve_flavor_data(self):
        """Get information about flavors to pass to a CachingStrategy object.

        """
        flavor_list = filter(self.flavor_filter,
                             self.nova_client.call("flavors.list"))
        unknown_flavors = filter(
            lambda f: self.known_flavors.get(f.id) is None, flavor_list)
        for flavor in unknown_flavors:
            # FIXME: This is super not going to work in general.
            # Need to rework how unknown flavors are identified in general.
            self.known_flavors[flavor.id] = lambda node: (
                node.properties['memory_mb'] == flavor.ram)
            LOG.warning("Detected an unknown flavor of id "
                        "%(flavor_id)s. Adding to known flavor list, and "
                        "identifying by amount of memory reported, which is "
                        "%(memory)s",
                        {'flavor_id': flavor.id,
                         'memory': flavor.ram})
        return map(self.curried_convert_nova_flavor, flavor_list)

    def retrieve_image_data(self):
        """Get information about images to pass to a CachingStrategy object.

        """
        self.glance_data = filter(self.image_filter,
                                  self.glance_client.call("images.list"))
        return map(convert_glance_image, self.glance_data)

    def issue_action(self, action):
        # TODO(ClifHouck) I know type-testing is generally not a good pattern,
        # but I'm not sure what would work better at this junction.
        if not isinstance(action, sb.StrategyAction):
            raise TypeError("OnMetalScout.issue_action: action is not of type "
                            "StrategyAction!")

        if isinstance(action, sb.CacheNode):
            return self.issue_cache_node(action)
        elif isinstance(action, sb.EjectNode):
            return self.issue_eject_node(action)

        LOG.error("Action is not a known "
                  "StrategyAction type! This method needs to be updated "
                  "in order to handle this action. Doing nothing for now.")

    def _find_glance_image(self, cache_node_action):
        # TODO(ClifHouck): O(n) search...
        for image in self.glance_data:
            if image.get('id') == cache_node_action.image_uuid:
                return image
        return None

    def issue_cache_node(self, cache_node_action):
        LOG.info("Issuing cache node operation on node %(node)s with "
                 "image %(image)s", {'node': cache_node_action.node_uuid,
                                     'image': cache_node_action.image_uuid})
        glance_image_data = self._find_glance_image(cache_node_action)

        if glance_image_data is None:
            LOG.error("Could not find glance data for the image "
                      "'%(image_id)s'! Doing nothing.",
                      {'image_id': cache_node_action.node_uuid})
            return

        image_url = glance_image_data.get('file')

        args = {
            'image_info': {
                'id': cache_node_action.image_uuid,
                'urls': [CONF.glance.api_endpoint + image_url],
                'checksum': cache_node_action.image_checksum
            }
        }

        try:
            self.ironic_client.call('node.vendor_passthru',
                                    node_id=cache_node_action.node_uuid,
                                    method='cache_image',
                                    args=args,
                                    http_method='POST')
        except exc.ArsenalException as e:
            LOG.exception(e)

    def issue_eject_node(self, eject_node_action):
        LOG.info("Issuing eject node command on node '%(node)s'.",
                 {'node': eject_node_action.node_uuid})
        try:
            LOG.debug("Sending %(node)s to 'managed' state.",
                      {'node': eject_node_action.node_uuid})
            self.ironic_client.call('node.set_provision_state',
                                    node_uuid=eject_node_action.node_uuid,
                                    state='manage')
            LOG.debug("Sending %(node)s to 'provide' state.",
                      {'node': eject_node_action.node_uuid})
            self.ironic_client.call('node.set_provision_state',
                                    node_uuid=eject_node_action.node_uuid,
                                    state='provide')
        except exc.ArsenalException as e:
            LOG.exception(e)
