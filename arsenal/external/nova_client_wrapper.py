# -*- encoding: utf-8 -*-
#
# Copyright 2015 Rackspace
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

import importlib

from novaclient import exceptions as nova_exc
from novaclient.v2 import client
from oslo.config import cfg

from arsenal.common import exception
from arsenal.external import client_wrapper
# from arsenal.i18n import _
from arsenal.openstack.common import log as logging


LOG = logging.getLogger(__name__)


opts = [
    cfg.StrOpt('admin_username',
               help='Nova keystone admin name'),
    cfg.StrOpt('admin_password',
               secret=True,
               help='Nova keystone admin password.'),
    cfg.StrOpt('admin_auth_token',
               secret=True,
               help='Nova keystone auth token.'),
    cfg.StrOpt('admin_url',
               help='Keystone public API endpoint.'),
    cfg.StrOpt('client_log_level',
               help='Log level override for novaclient. Set this in '
                    'order to override the global "default_log_levels", '
                    '"verbose", and "debug" settings.'),
    cfg.StrOpt('admin_tenant_name',
               help='Nova keystone tenant name.'),
    cfg.IntOpt('api_max_retries',
               default=60,
               help='How many retries when a request does conflict.'),
    cfg.IntOpt('api_retry_interval',
               default=2,
               help='How often to retry in seconds when a request '
                    'does conflict'),
    cfg.StrOpt('region_name',
               help='Nova region name.'),
    cfg.StrOpt('service_name',
               help='Nova service name.'),
    cfg.StrOpt('auth_system',
               default='keystone',
               help='Nova auth_system argument.'),
    cfg.StrOpt('auth_plugin',
               help='The authorization plugin to load for nova.'),
    cfg.StrOpt('auth_plugin_obj',
               help='The authorization plugin to load for nova.'),

]

nova_group = cfg.OptGroup(name='nova',
                          title='Nova Options')

CONF = cfg.CONF
CONF.register_group(nova_group)
CONF.register_opts(opts, nova_group)

first_not_none = client_wrapper.first_not_none


class NovaClientWrapper(client_wrapper.OpenstackClientWrapper):
    """Nova client wrapper class that encapsulates retry logic."""

    def __init__(self):
        """Initialise the NovaClientWrapper for use."""
        super(NovaClientWrapper, self).__init__(
            retry_exceptions=(nova_exc.ConnectionRefused,
                              nova_exc.Conflict),
            auth_exceptions=(nova_exc.Unauthorized),
            name="Nova")

    def _get_new_client(self):
        auth_token = first_not_none([CONF.nova.admin_auth_token,
                                     CONF.client_wrapper.os_auth_token])
        auth_plugin = None
        if CONF.nova.auth_plugin is not None:
            auth_plugin_module = importlib.import_module(CONF.nova.auth_plugin)
            auth_plugin = getattr(auth_plugin_module,
                                  CONF.nova.auth_plugin_obj)()

        # Instead of just using client_wrapper configuration options,
        # provide them as a fallback if nova configuration options are not
        # defined.
        if auth_token is None:
            kwargs = {'username':
                      first_not_none([CONF.nova.admin_username,
                                      CONF.client_wrapper.os_username]),
                      'api_key':
                      first_not_none([CONF.nova.admin_password,
                                      CONF.client_wrapper.os_password]),
                      'auth_url':
                      first_not_none([CONF.nova.admin_url,
                                      CONF.client_wrapper.os_api_url]),
                      'project_id':
                      first_not_none([CONF.nova.admin_tenant_name,
                                      CONF.client_wrapper.os_tenant_name]),
                      'insecure': True,
                      'service_name':
                      first_not_none([CONF.nova.service_name,
                                      CONF.client_wrapper.service_name]),
                      'region_name':
                      first_not_none([CONF.nova.region_name,
                                      CONF.client_wrapper.region_name]),
                      'auth_system':
                      first_not_none([CONF.nova.auth_system,
                                      CONF.client_wrapper.auth_system]),
                      'auth_plugin': auth_plugin}
        else:
            kwargs = {'auth_token': auth_token,
                      'auth_url':
                      first_not_none([CONF.nova.admin_url,
                                     CONF.client_wrapper.os_api_url])}

        try:
            cli = client.Client(**kwargs)
        except nova_exc.Unauthorized:
            msg = "Unable to authenticate Nova client."
            LOG.error(msg)
            raise exception.ArsenalException(msg)

        return cli
