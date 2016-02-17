# Copyright 2014 Red Hat, Inc.
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

import mock
from novaclient import client as nova_client
from oslo_config import cfg

from arsenal.external import nova_client_wrapper as client_wrapper
from arsenal.tests.unit import base as test_base


CONF = cfg.CONF


class FakeFlavorClient(object):
    def list(self, detail=False):
        return []


class FakeClient(object):
    flavor = FakeFlavorClient()


FAKE_CLIENT = FakeClient()


def get_new_fake_client(*args, **kwargs):
    return FakeClient()


class NovaClientWrapperTestCase(test_base.TestCase):

    def setUp(self):
        super(NovaClientWrapperTestCase, self).setUp()
        self.novaclient = client_wrapper.NovaClientWrapper()
        # Do not waste time sleeping
        cfg.CONF.set_override('call_retry_interval', 0, 'client_wrapper')
        # Setup some config variables.
        cfg.CONF.set_override('api_version', '2', 'nova')
        cfg.CONF.set_override('admin_username', 'myusername', 'nova')
        cfg.CONF.set_override('admin_password', 'somepass', 'nova')
        cfg.CONF.set_override('admin_tenant_name', 'garfield', 'nova')
        cfg.CONF.set_override('admin_url', 'some_host', 'nova')
        cfg.CONF.set_override('service_name', 'clouds', 'nova')
        cfg.CONF.set_override('region_name', 'ord', 'nova')

    @mock.patch.object(nova_client, 'Client')
    def test__get_client(self, mock_nova_cli):
        novaclient = client_wrapper.NovaClientWrapper()
        # dummy call to have _get_client() called
        novaclient.call("flavor.list")
        expected_args = (
            CONF.nova.api_version,
            CONF.nova.admin_username,
            CONF.nova.admin_password,
            CONF.nova.admin_tenant_name,
            CONF.nova.admin_url,
        )
        expected_kw_args = {
            'insecure': True,
            'service_name': CONF.nova.service_name,
            'region_name': CONF.nova.region_name,
            'auth_system': CONF.nova.auth_system,
            'auth_plugin': None
        }
        mock_nova_cli.assert_called_once_with(*expected_args,
                                              **expected_kw_args)
