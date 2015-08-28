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
from novaclient.v2 import client as nova_client
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

    @mock.patch.object(nova_client, 'Client')
    def test__get_client_no_auth_token(self, mock_nova_cli):
        self.flags(admin_auth_token=None, group='nova')
        novaclient = client_wrapper.NovaClientWrapper()
        # dummy call to have _get_client() called
        novaclient.call("flavor.list")
        expected = {'username': CONF.nova.admin_username,
                    'api_key': CONF.nova.admin_password,
                    'auth_url': CONF.nova.admin_url,
                    'project_id': CONF.nova.admin_tenant_name,
                    'insecure': True,
                    'service_name': CONF.nova.service_name,
                    'region_name': CONF.nova.region_name,
                    'auth_system': CONF.nova.auth_system,
                    'auth_plugin': None}
        mock_nova_cli.assert_called_once_with(**expected)

    @mock.patch.object(nova_client, 'Client')
    def test__get_client_with_auth_token(self, mock_nova_cli):
        self.flags(admin_auth_token='fake-token', group='nova')
        novaclient = client_wrapper.NovaClientWrapper()
        # dummy call to have _get_client() called
        novaclient.call("flavor.list")
        expected = {'auth_token': 'fake-token',
                    'auth_url': CONF.nova.admin_url}
        mock_nova_cli.assert_called_once_with(**expected)
