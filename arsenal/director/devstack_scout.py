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

from arsenal.director import onmetal_scout as onmetal
from arsenal.openstack.common import log

LOG = log.getLogger(__name__)

CONF = cfg.CONF


def is_baremetal_image(glance_image):
    return glance_image.name == 'cirros-0.3.2-x86_64-disk'


def is_baremetal_flavor(flavor):
    return flavor.name == "baremetal"


class DevstackScout(onmetal.OnMetalScout):
    def retrieve_image_data(self):
        """Get information about images to pass to a CachingStrategy object.

        """
        self.glance_data = filter(is_baremetal_image,
                                  self.glance_client.call("images.list"))
        return map(onmetal.convert_glance_image, self.glance_data)

    def retrieve_flavor_data(self):
        """Get information about flavors to pass to a CachingStrategy object.

        """
        flavor_list = filter(is_baremetal_flavor,
                             self.nova_client.call("flavors.list"))
        unknown_flavors = filter(lambda f: (onmetal.KNOWN_FLAVORS.get(f.id)
                                            is None),
                                 flavor_list)
        for flavor in unknown_flavors:
            onmetal.KNOWN_FLAVORS[flavor.id] = lambda node: (
                node.properties['memory_mb'] == flavor.ram)
            LOG.warning("Detected an unknown flavor of id "
                        "%(flavor_id)s. Adding to known flavor list, and "
                        "identifying by amount of memory reported, which is "
                        "%(memory)s",
                        {'flavor_id': flavor.id,
                         'memory': flavor.ram})
        return map(onmetal.convert_nova_flavor, flavor_list)
