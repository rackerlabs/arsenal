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

from arsenal.director import openstack_scout


def is_baremetal_image(glance_image):
    return glance_image.name == 'cirros-0.3.2-x86_64-disk'


def is_baremetal_flavor(flavor):
    return flavor.name == "baremetal"


class DevstackScout(openstack_scout.OpenstackScout):
    def __init__(self):
        """Constructs a scout suitable for use against a Devstack deployment.

        See http://docs.openstack.org/developer/devstack/
        and http://docs.openstack.org/developer/ironic/dev/dev-quickstart.\
                html#deploying-ironic-with-devstack
        for more about using Ironic and Devstack together.
        """
        super(DevstackScout, self).__init__(
           flavor_filter=is_baremetal_flavor,
           image_filter=is_baremetal_image,
           glance_auth_token_func=None,
           known_flavors=None)
