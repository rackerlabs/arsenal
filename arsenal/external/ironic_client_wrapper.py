# coding=utf-8
#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
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

# Taken from 806312a09933e6be0ee6f4f07dff01caf2345cdf of
# https://github.com/openstack/nova/ in ./nova/virt/ironic/client_wrapper.py
# and slightly adapted for Arsenal

import ironicclient
from oslo.config import cfg

from arsenal.common import exception
from arsenal.external import client_wrapper
# from arsenal.i18n import _
from arsenal.openstack.common import log as logging


LOG = logging.getLogger(__name__)


opts = [
    cfg.IntOpt('api_version',
               default=1,
               help='Version of Ironic API service endpoint.'),
    cfg.StrOpt('api_endpoint',
               help='URL for Ironic API endpoint.'),
    cfg.StrOpt('admin_username',
               help='Ironic keystone admin name'),
    cfg.StrOpt('admin_password',
               help='Ironic keystone admin password.'),
    cfg.StrOpt('admin_auth_token',
               help='Ironic keystone auth token.'),
    cfg.StrOpt('admin_url',
               help='Keystone public API endpoint.'),
    cfg.StrOpt('client_log_level',
               help='Log level override for ironicclient. Set this in '
                    'order to override the global "default_log_levels", '
                    '"verbose", and "debug" settings.'),
    cfg.StrOpt('admin_tenant_name',
               help='Ironic keystone tenant name.'),
    cfg.IntOpt('api_max_retries',
               default=60,
               help='How many retries when a request does conflict.'),
    cfg.IntOpt('api_retry_interval',
               default=2,
               help='How often to retry in seconds when a request '
                    'does conflict'),
    ]

ironic_group = cfg.OptGroup(name='ironic',
                            title='Ironic Options')

CONF = cfg.CONF
CONF.register_group(ironic_group)
CONF.register_opts(opts, ironic_group)

first_not_none = client_wrapper.first_not_none


class IronicClientWrapper(client_wrapper.OpenstackClientWrapper):
    """Ironic client wrapper class that encapsulates retry logic."""

    def __init__(self):
        """Initialise the IronicClientWrapper for use."""
        super(IronicClientWrapper, self).__init__(
            retry_exceptions=(ironicclient.exc.ServiceUnavailable,
                              ironicclient.exc.ConnectionRefused,
                              ironicclient.exc.Conflict),
            auth_exceptions=(ironicclient.exc.Unauthorized),
            name="Ironic")

    def _get_new_client(self):
        auth_token = first_not_none([CONF.ironic.admin_auth_token,
                                     CONF.client_wrapper.os_auth_token])

        if auth_token is None:
            kwargs = {'os_username':
                      first_not_none([CONF.ironic.admin_username,
                                      CONF.client_wrapper.os_username]),
                      'os_password':
                      first_not_none([CONF.ironic.admin_password,
                                      CONF.client_wrapper.os_password]),
                      'os_auth_url':
                      first_not_none([CONF.ironic.admin_url,
                                      CONF.client_wrapper.os_api_url]),
                      'os_tenant_name':
                      first_not_none([CONF.ironic.admin_tenant_name,
                                      CONF.client_wrapper.os_tenant_name]),
                      'os_service_type': 'baremetal',
                      'os_endpoint_type': 'public',
                      'ironic_url': CONF.ironic.api_endpoint
                      }
        else:
            kwargs = {'os_auth_token': auth_token,
                      'ironic_url': CONF.client_wrapper.os_api_url}

        try:
            cli = ironicclient.client.get_client(CONF.ironic.api_version,
                                                 **kwargs)

        except ironicclient.exc.Unauthorized:
            msg = "Unable to authenticate Ironic client."
            LOG.error(msg)
            raise exception.ArsenalException(msg)

        return cli
