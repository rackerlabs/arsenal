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

import re

from oslo_log import log

from arsenal.director import openstack_scout


LOG = log.getLogger(__name__)


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


KNOWN_V1_FLAVORS = {
    'onmetal-compute1': lambda node: node.properties['memory_mb'] == 32768,
    'onmetal-io1': lambda node: node.properties['memory_mb'] == 131072,
    'onmetal-memory1': lambda node: node.properties['memory_mb'] == 524288,
}


def is_onmetal_image(glance_image, specific_flavor_class):
    flavor_classes = glance_image.get('flavor_classes')

    # Sometimes an image will have no class! Shocking!
    if flavor_classes is None:
        return False

    return ('!onmetal' not in flavor_classes and
            specific_flavor_class in flavor_classes and
            glance_image.get('vm_mode') == 'metal' and
            glance_image.get('visibility') == 'public')


def is_onmetal_v1_image(glance_image):
    return is_onmetal_image(glance_image, 'onmetal')


def is_onmetal_v1_flavor(flavor):
    return len(flavor.id) > 8 and flavor.id[0:8] == 'onmetal-'


class OnMetalV1Scout(openstack_scout.OpenstackScout):
    """Scouts and filters data for the OnMetal V1 Rackspace service."""
    def __init__(self):
        super(OnMetalV1Scout, self).__init__(
            flavor_filter=is_onmetal_v1_flavor,
            image_filter=is_onmetal_v1_image,
            glance_auth_token_func=get_pyrax_token,
            known_flavors=KNOWN_V1_FLAVORS)


def is_v2_flavor_generic(ironic_node,
                         expected_memory_mb,
                         expected_local_gb,
                         expected_cpus):
    properties = ironic_node.get('properties')
    if properties is None:
        return False

    memory_mb = properties.get('memory_mb')
    local_gb = properties.get('local_gb')
    cpus = properties.get('cpus')

    return (memory_mb == expected_memory_mb and
            local_gb == expected_local_gb and
            cpus == expected_cpus)


KNOWN_V2_FLAVORS = {
    'onmetal-general2-small':
        lambda node: is_v2_flavor_generic(node, 32768, 800, 12),
    'onmetal-general2-medium':
        lambda node: is_v2_flavor_generic(node, 65536, 800, 24),
    'onmetal-general2-large':
        lambda node: is_v2_flavor_generic(node, 131072, 800, 24),
    'onmetal-io2':
        lambda node: is_v2_flavor_generic(node, 131072, 120, 40),
}


def is_onmetal_v2_image(glance_image):
    return is_onmetal_image(glance_image, 'onmetal2')


ONMETAL_V2_FLAVOR_NAME_REGEX = re.compile('onmetal-[a-z-]+2')


def is_onmetal_v2_flavor(flavor):
    match_result = ONMETAL_V2_FLAVOR_NAME_REGEX.match(flavor.id)
    return match_result is not None


class OnMetalV2Scout(openstack_scout.OpenstackScout):
    """Scouts and filters data for the OnMetal V2 Rackspace service."""
    def __init__(self):
        super(OnMetalV2Scout, self).__init__(
            flavor_filter=is_onmetal_v2_flavor,
            image_filter=is_onmetal_v2_image,
            glance_auth_token_func=get_pyrax_token,
            known_flavors=KNOWN_V2_FLAVORS)
