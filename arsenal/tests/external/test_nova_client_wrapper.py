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
from novaclient import exceptions as nova_exception
from novaclient.v1_1 import client as nova_client
from oslo.config import cfg

from arsenal.common import exception
from arsenal.external import nova_client_wrapper as client_wrapper
from arsenal.tests import base as test_base


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
        cfg.CONF.set_override('api_retry_interval', 0, 'nova')

    @mock.patch.object(client_wrapper.NovaClientWrapper, '_multi_getattr')
    @mock.patch.object(client_wrapper.NovaClientWrapper, '_get_client')
    def test_call_good_no_args(self, mock_get_client, mock_multi_getattr):
        mock_get_client.return_value = FAKE_CLIENT
        self.novaclient.call("flavor.list")
        mock_get_client.assert_called_once_with()
        mock_multi_getattr.assert_called_once_with(FAKE_CLIENT, "flavor.list")
        mock_multi_getattr.return_value.assert_called_once_with()

    @mock.patch.object(client_wrapper.NovaClientWrapper, '_multi_getattr')
    @mock.patch.object(client_wrapper.NovaClientWrapper, '_get_client')
    def test_call_good_with_args(self, mock_get_client, mock_multi_getattr):
        mock_get_client.return_value = FAKE_CLIENT
        self.novaclient.call("flavor.list", 'test', associated=True)
        mock_get_client.assert_called_once_with()
        mock_multi_getattr.assert_called_once_with(FAKE_CLIENT, "flavor.list")
        mock_multi_getattr.return_value.assert_called_once_with(
            'test', associated=True)

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

    @mock.patch.object(client_wrapper.NovaClientWrapper, '_multi_getattr')
    @mock.patch.object(client_wrapper.NovaClientWrapper, '_get_client')
    def test_call_fail(self, mock_get_client, mock_multi_getattr):
        cfg.CONF.set_override('api_max_retries', 2, 'nova')
        test_obj = mock.Mock()
        test_obj.side_effect = (
            nova_exception.ConnectionRefused('ConnectionRefused'))
        mock_multi_getattr.return_value = test_obj
        mock_get_client.return_value = FAKE_CLIENT
        self.assertRaises(exception.ArsenalException, self.novaclient.call,
                          "flavor.list")
        self.assertEqual(2, test_obj.call_count)

    @mock.patch.object(client_wrapper.NovaClientWrapper, '_multi_getattr')
    @mock.patch.object(client_wrapper.NovaClientWrapper, '_get_client')
    def test_call_fail_unexpected_exception(self, mock_get_client,
                                            mock_multi_getattr):
        test_obj = mock.Mock()
        test_obj.side_effect = nova_exception.NotFound('NotFound')
        mock_multi_getattr.return_value = test_obj
        mock_get_client.return_value = FAKE_CLIENT
        self.assertRaises(nova_exception.NotFound,
                          self.novaclient.call, "flavor.list")

    @mock.patch.object(nova_client, 'Client')
    def test__get_client_unauthorized(self, mock_get_client):
        mock_get_client.side_effect = (
            nova_exception.Unauthorized('NotAuthorized'))
        self.assertRaises(exception.ArsenalException,
                          self.novaclient._get_client)

    @mock.patch.object(nova_client, 'Client')
    def test__get_client_unexpected_exception(self, mock_get_client):
        mock_get_client.side_effect = (
            nova_exception.ConnectionRefused('Refused'))
        self.assertRaises(nova_exception.ConnectionRefused,
                          self.novaclient._get_client)

    def test__multi_getattr_good(self):
        response = self.novaclient._multi_getattr(FAKE_CLIENT, "flavor.list")
        self.assertEqual(FAKE_CLIENT.flavor.list, response)

    def test__multi_getattr_fail(self):
        self.assertRaises(AttributeError, self.novaclient._multi_getattr,
                          FAKE_CLIENT, "nonexistent")

    @mock.patch.object(nova_client, 'Client')
    def test__client_is_cached(self, mock_get_client):
        mock_get_client.side_effect = get_new_fake_client
        novaclient = client_wrapper.NovaClientWrapper()
        first_client = novaclient._get_client()
        second_client = novaclient._get_client()
        self.assertEqual(id(first_client), id(second_client))

    @mock.patch.object(nova_client, 'Client')
    def test__invalidate_cached_client(self, mock_get_client):
        mock_get_client.side_effect = get_new_fake_client
        novaclient = client_wrapper.NovaClientWrapper()
        first_client = novaclient._get_client()
        novaclient._invalidate_cached_client()
        second_client = novaclient._get_client()
        self.assertNotEqual(id(first_client), id(second_client))

    @mock.patch.object(nova_client, 'Client')
    def test_call_uses_cached_client(self, mock_get_client):
        mock_get_client.side_effect = get_new_fake_client
        novaclient = client_wrapper.NovaClientWrapper()
        for n in range(0, 4):
            novaclient.call("flavor.list")
        self.assertEqual(1, mock_get_client.call_count)
