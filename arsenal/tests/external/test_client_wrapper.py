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
from oslo_config import cfg

from arsenal.common import exception
from arsenal.external import client_wrapper
from arsenal.tests import base as test_base


CONF = cfg.CONF


class FakeFlavorClient(object):
    def list(self, detail=False):
        return []


class FakeClient(object):
    flavor = FakeFlavorClient()


def get_new_fake_client(*args, **kwargs):
    return FakeClient()


class FakeUnauthorizedException(Exception):
    pass


class FakeForbiddenException(Exception):
    pass


class FakeRetryOnThisException(Exception):
    pass


class FakeUnexpectedException(Exception):
    pass


class FakeClientWrapper(client_wrapper.OpenstackClientWrapper):

    def __init__(self):
        super(FakeClientWrapper, self).__init__(
            retry_exceptions=(FakeRetryOnThisException),
            auth_exceptions=(FakeUnauthorizedException,
                             FakeForbiddenException),
            name="FakeClient")

    def _get_new_client(self):
        return get_new_fake_client()


FAKE_CLIENT = FakeClient()


class OpenstackClientWrapperTestCase(test_base.TestCase):

    def setUp(self):
        super(OpenstackClientWrapperTestCase, self).setUp()
        # Yes, the client is fake, but we're only testing relevant behavior
        # in the base class.
        self.openstackclient = FakeClientWrapper()
        # Do not waste time sleeping
        cfg.CONF.set_override('call_retry_interval', 0, 'client_wrapper')

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, '_multi_getattr')
    @mock.patch.object(FakeClientWrapper, '_get_new_client')
    def test_call_good_no_args(self, mock_get_new_client, mock_multi_getattr):
        mock_get_new_client.return_value = FAKE_CLIENT
        self.openstackclient.call("flavor.list")
        mock_get_new_client.assert_called_once_with()
        mock_multi_getattr.assert_called_once_with(FAKE_CLIENT, "flavor.list")
        mock_multi_getattr.return_value.assert_called_once_with()

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, '_multi_getattr')
    @mock.patch.object(FakeClientWrapper, '_get_new_client')
    def test_call_good_with_args(self, mock_get_client, mock_multi_getattr):
        mock_get_client.return_value = FAKE_CLIENT
        self.openstackclient.call("flavor.list", 'test', associated=True)
        mock_get_client.assert_called_once_with()
        mock_multi_getattr.assert_called_once_with(FAKE_CLIENT, "flavor.list")
        mock_multi_getattr.return_value.assert_called_once_with(
            'test', associated=True)

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, '_multi_getattr')
    @mock.patch.object(FakeClientWrapper, '_get_new_client')
    def test_call_fail(self, mock_get_new_client, mock_multi_getattr):
        cfg.CONF.set_override('call_max_retries', 2, 'client_wrapper')
        test_obj = mock.Mock()
        test_obj.side_effect = (FakeRetryOnThisException('ConnectionRefused'))
        mock_multi_getattr.return_value = test_obj
        mock_get_new_client.return_value = FAKE_CLIENT
        self.assertRaises(exception.ArsenalException,
                          self.openstackclient.call,
                          "flavor.list")
        self.assertEqual(2, test_obj.call_count)

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, '_multi_getattr')
    @mock.patch.object(FakeClientWrapper, '_get_new_client')
    def test_call_fail_unexpected_exception(self, mock_get_new_client,
                                            mock_multi_getattr):
        test_obj = mock.Mock()
        test_obj.side_effect = FakeUnexpectedException('NotFound')
        mock_multi_getattr.return_value = test_obj
        mock_get_new_client.return_value = FAKE_CLIENT
        self.assertRaises(FakeUnexpectedException,
                          self.openstackclient.call, "flavor.list")

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, '_multi_getattr')
    @mock.patch.object(FakeClientWrapper, '_get_new_client')
    def test_call_unauthorized_causes_new_clients(self,
                                                  mock_get_new_client,
                                                  mock_multi_getattr):
        cfg.CONF.set_override('call_max_retries', 3, 'client_wrapper')
        test_obj = mock.Mock()
        test_obj.side_effect = FakeForbiddenException('Forbidden')
        mock_multi_getattr.return_value = test_obj
        mock_get_new_client.return_value = FAKE_CLIENT
        self.assertRaises(exception.ArsenalException,
                          self.openstackclient.call,
                          "flavor.list")
        self.assertEqual(3, mock_get_new_client.call_count)

    def test__multi_getattr_good(self):
        response = self.openstackclient._multi_getattr(FAKE_CLIENT,
                                                       "flavor.list")
        self.assertEqual(FAKE_CLIENT.flavor.list, response)

    def test__multi_getattr_fail(self):
        self.assertRaises(AttributeError, self.openstackclient._multi_getattr,
                          FAKE_CLIENT, "nonexistent")

    def test__client_is_cached(self):
        openstackclient = FakeClientWrapper()
        first_client = openstackclient._get_client()
        second_client = openstackclient._get_client()
        self.assertEqual(id(first_client), id(second_client))

    def test__invalidate_cached_client(self):
        openstackclient = FakeClientWrapper()
        first_client = openstackclient._get_client()
        openstackclient._invalidate_cached_client()
        second_client = openstackclient._get_client()
        self.assertNotEqual(id(first_client), id(second_client))

    @mock.patch.object(FakeClientWrapper, '_get_new_client')
    def test_call_uses_cached_client(self, mock_get_new_client):
        mock_get_new_client.side_effect = lambda: get_new_fake_client()
        openstackclient = FakeClientWrapper()
        for n in range(0, 4):
            openstackclient.call("flavor.list")
        self.assertEqual(1, mock_get_new_client.call_count)
