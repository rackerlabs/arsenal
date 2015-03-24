# Copyright 2015 Rackspace
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

from glanceclient.v2 import client as glance_client
import mock
from oslo.config import cfg

from arsenal.external import glance_client_wrapper as client_wrapper
from arsenal.tests import base as test_base

CONF = cfg.CONF


class GlanceClientWrapperTestCase(test_base.TestCase):

    def setUp(self):
        super(GlanceClientWrapperTestCase, self).setUp()
        self.glanceclient = client_wrapper.GlanceClientWrapper()
        # Do not waste time sleeping
        cfg.CONF.set_override('call_retry_interval', 0, 'client_wrapper')

    @mock.patch.object(glance_client, 'Client')
    def test__get_client_no_auth_token(self, mock_ir_cli):
        # FIXME: Sort pyrax situation out.
        return
        self.flags(api_endpoint='glance-endpoint', group='glance')
        self.flags(admin_auth_token=None, group='glance')
        glanceclient = client_wrapper.GlanceClientWrapper()
        # dummy call to have Client() called
        glanceclient.call("image.list")
        expected = {'username': CONF.glance.admin_username,
                    'password': CONF.glance.admin_password,
                    'auth_url': CONF.glance.admin_url,
                    'tenant_name': CONF.glance.admin_tenant_name,
                    'tenant_id': CONF.glance.admin_tenant_id,
                    'region_name': CONF.glance.region_name}

        mock_ir_cli.assert_called_once_with(CONF.glance.api_endpoint,
                                            **expected)

    @mock.patch.object(glance_client, 'Client')
    def test__get_client_with_auth_token(self, mock_ir_cli):
        self.flags(api_endpoint='glance-endpoint', group='glance')
        self.flags(admin_auth_token='fake-token', group='glance')
        glanceclient = client_wrapper.GlanceClientWrapper()
        # dummy call to have _get_client() called
        glanceclient.call("image.list")
        expected = {'token': 'fake-token'}
        mock_ir_cli.assert_called_once_with(CONF.glance.api_endpoint,
                                            **expected)
