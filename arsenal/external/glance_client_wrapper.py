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

import glanceclient
from glanceclient.v2 import client
from keystoneclient.v2_0 import client as keystone_client
from oslo.config import cfg

from arsenal.common import exception
from arsenal.external import client_wrapper
from arsenal.openstack.common import log as logging

LOG = logging.getLogger(__name__)


opts = [
    cfg.IntOpt('api_version',
               default=2,
               help='Version of Glance API service endpoint.'),
    cfg.StrOpt('api_endpoint',
               help='URL for Glance API endpoint.'),
    cfg.StrOpt('auth_endpoint',
               help='URL for Auth endpoint.'),
    cfg.StrOpt('admin_username',
               help='Glance keystone admin name'),
    cfg.StrOpt('admin_password',
               help='Glance keystone admin password.'),
    cfg.StrOpt('admin_auth_token',
               help='Glance keystone auth token.'),
    cfg.StrOpt('client_log_level',
               help='Log level override for glanceclient. Set this in '
                    'order to override the global "default_log_levels", '
                    '"verbose", and "debug" settings.'),
    cfg.StrOpt('admin_tenant_name',
               help='Glance keystone tenant name.'),
    cfg.StrOpt('admin_tenant_id',
               help='Glance keystone tenant id.'),
    cfg.StrOpt('region_name',
               help='Glance region name.'),
]

glance_group = cfg.OptGroup(name='glance',
                            title='Glance Options')

CONF = cfg.CONF
CONF.register_group(glance_group)
CONF.register_opts(opts, glance_group)

first_not_none = client_wrapper.first_not_none


class GlanceClientWrapper(client_wrapper.OpenstackClientWrapper):
    """Glance client wrapper class that encapsulates retry logic."""

    def __init__(self):
        """Initialise the GlanceClientWrapper for use."""
        super(GlanceClientWrapper, self).__init__(
            retry_exceptions=(glanceclient.exc.Conflict),
            auth_exceptions=(glanceclient.exc.Unauthorized),
            name="Glance")

    def _get_new_client(self):
        auth_token = first_not_none([CONF.glance.admin_auth_token,
                                     CONF.client_wrapper.os_auth_token])
        endpoint = first_not_none([CONF.glance.api_endpoint,
                                   CONF.client_wrapper.os_api_url])
        if endpoint is None:
            raise exception.ArsenalException(
                "There was no endpoint specified for the glance client!")

        if auth_token is None:
            kwargs = {'username':
                      first_not_none([CONF.glance.admin_username,
                                      CONF.client_wrapper.os_username]),
                      'password':
                      first_not_none([CONF.glance.admin_password,
                                      CONF.client_wrapper.os_password]),
                      'auth_url':
                      first_not_none([CONF.glance.auth_endpoint,
                                      CONF.client_wrapper.os_api_url]),
                      'tenant_name':
                      first_not_none([CONF.glance.admin_tenant_name,
                                      CONF.client_wrapper.os_tenant_name]),
                      'tenant_id':
                      first_not_none([CONF.glance.admin_tenant_id,
                                      CONF.client_wrapper.os_tenant_id]),
                      'region_name':
                      first_not_none([CONF.glance.region_name,
                                      CONF.client_wrapper.region_name]),
                      'insecure': True
                      }

            # NOTE(ClifHouck): Glanceclient doesn't currently actually try
            # to auth, so get a token from keystone client instead.
            ks_cli = keystone_client.Client(**kwargs)
            auth_token_obj = (
                ks_cli.get_raw_token_from_identity_service(**kwargs))
            auth_token = auth_token_obj['token']['id']
            kwargs = {'token': auth_token}
        else:
            kwargs = {'token': auth_token}

        try:
            cli = client.Client(endpoint, **kwargs)

        except glanceclient.exc.Unauthorized:
            msg = "Unable to authenticate Glance client."
            LOG.error(msg)
            raise exception.ArsenalException(msg)

        return cli
