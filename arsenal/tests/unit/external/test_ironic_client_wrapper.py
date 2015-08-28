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

from ironicclient import client as ironic_client
import mock
from oslo_config import cfg

from arsenal.external import ironic_client_wrapper as client_wrapper
from arsenal.tests.unit import base as test_base
from arsenal.tests.unit.external import ironic_utils

CONF = cfg.CONF

FAKE_CLIENT = ironic_utils.FakeClient()


def get_new_fake_client(*args, **kwargs):
    return ironic_utils.FakeClient()


class IronicClientWrapperTestCase(test_base.TestCase):

    def setUp(self):
        super(IronicClientWrapperTestCase, self).setUp()
        self.ironicclient = client_wrapper.IronicClientWrapper()
        # Do not waste time sleeping
        cfg.CONF.set_override('call_retry_interval', 0, 'client_wrapper')

    @mock.patch.object(ironic_client, 'get_client')
    def test__get_client_no_auth_token(self, mock_ir_cli):
        self.flags(admin_auth_token=None, group='ironic')
        ironicclient = client_wrapper.IronicClientWrapper()
        # dummy call to have _get_client() called
        ironicclient.call("node.list")
        expected = {'os_username': CONF.ironic.admin_username,
                    'os_password': CONF.ironic.admin_password,
                    'os_auth_url': CONF.ironic.admin_url,
                    'os_tenant_name': CONF.ironic.admin_tenant_name,
                    'os_service_type': 'baremetal',
                    'os_endpoint_type': 'public',
                    'ironic_url': CONF.ironic.api_endpoint}
        mock_ir_cli.assert_called_once_with(CONF.ironic.api_version,
                                            **expected)

    @mock.patch.object(ironic_client, 'get_client')
    def test__get_client_with_auth_token(self, mock_ir_cli):
        self.flags(admin_auth_token='fake-token', group='ironic')
        ironicclient = client_wrapper.IronicClientWrapper()
        # dummy call to have _get_client() called
        ironicclient.call("node.list")
        expected = {'os_auth_token': 'fake-token',
                    'ironic_url': CONF.ironic.api_endpoint}
        mock_ir_cli.assert_called_once_with(CONF.ironic.api_version,
                                            **expected)
