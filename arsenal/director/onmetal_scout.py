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

from arsenal.common import exception as exc
from arsenal.director import scout
import arsenal.external.glance_client_wrapper as gcw
import arsenal.external.ironic_client_wrapper as icw
import arsenal.external.nova_client_wrapper as ncw
from arsenal.openstack.common import log
from arsenal.strategy import base as sb


LOG = log.getLogger(__name__)

CONF = cfg.CONF


def get_pyrax_token(**kwargs):
    # NOTE(ClifHouck) support Rackspace-specific auth for OnMetal.
    # I'm refusing to put pyrax into requirements for Arsenal, because Arsenal
    # should not be Rackspace-centric.
    try:
        import pyrax
    except ImportError as e:
        LOG.error("Could not import pyrax for OnMetalScout. "
                  "Please install pyrax!")
        raise e

    pyrax.set_setting('identity_type', 'rackspace')
    pyrax.set_setting('auth_endpoint', kwargs.get('auth_url'))
    pyrax.set_credentials(kwargs.get('username'), kwargs.get('password'))
    return pyrax.identity.auth_token


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


KNOWN_FLAVORS = {
    'onmetal-compute1': lambda node: node.properties['memory_mb'] == 32768,
    'onmetal-io1': lambda node: node.properties['memory_mb'] == 131072,
    'onmetal-memory1': lambda node: node.properties['memory_mb'] == 524288,
}


def convert_ironic_node(ironic_node):
    flavor_name = None

    for flavor, ident_func in KNOWN_FLAVORS.iteritems():
        if ident_func(ironic_node):
            flavor_name = flavor
            break

    if flavor_name is None:
        LOG.error("Unable to identify flavor of node '%(node)s'",
                  {'node': ironic_node.uuid})
        return None

    return sb.NodeInput(ironic_node.uuid,
                        flavor_name,
                        is_node_provisioned(ironic_node),
                        is_node_cached(ironic_node),
                        get_node_cached_image_uuid(ironic_node))


def is_onmetal_image(glance_image):
    return (glance_image.get('flavor_classes') == 'onmetal' and
            glance_image.get('vm_mode') == 'metal' and
            glance_image.get('visibility') == 'public')


def convert_glance_image(glance_image):
    return sb.ImageInput(glance_image.get('name'),
                         glance_image.get('id'),
                         glance_image.get('checksum'))


def is_onmetal_flavor(flavor):
    return len(flavor.id) > 8 and flavor.id[0:8] == 'onmetal-'


def convert_nova_flavor(nova_flavor):
    return sb.FlavorInput(nova_flavor.id,
                          KNOWN_FLAVORS.get(nova_flavor.id))


class OnMetalScout(scout.Scout):
    """Specifically scouts and filters data for the OnMetal Rackspace service.

    """
    def __init__(self):
        self.ironic_client = icw.IronicClientWrapper()
        self.nova_client = ncw.NovaClientWrapper()
        self.glance_client = gcw.GlanceClientWrapper(get_pyrax_token)
        self.glance_data = []

    def retrieve_node_data(self):
        """Get information about nodes to pass to a CachingStrategy object.

        """
        node_list = self.ironic_client.call("node.list", limit=0, detail=True)
        return filter(lambda n: n is not None,
                      map(convert_ironic_node, node_list))

    def retrieve_flavor_data(self):
        """Get information about flavors to pass to a CachingStrategy object.

        """
        flavor_list = filter(is_onmetal_flavor,
                             self.nova_client.call("flavors.list"))
        unknown_flavors = filter(lambda f: KNOWN_FLAVORS.get(f.id) is None,
                                 flavor_list)
        for flavor in unknown_flavors:
            KNOWN_FLAVORS[flavor.id] = lambda node: (
                node.properties['memory_mb'] == flavor.ram)
            LOG.warning("Detected an unknown flavor of id "
                        "%(flavor_id)s. Adding to known flavor list, and "
                        "identifying by amount of memory reported, which is "
                        "%(memory)s",
                        {'flavor_id': flavor.id,
                         'memory': flavor.ram})
        return map(convert_nova_flavor, flavor_list)

    def retrieve_image_data(self):
        """Get information about images to pass to a CachingStrategy object.

        """
        self.glance_data = filter(is_onmetal_image,
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
