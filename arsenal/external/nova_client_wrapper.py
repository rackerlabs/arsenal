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

import time

from novaclient import exceptions as nova_exc
from novaclient.v3 import client
from oslo.config import cfg

from arsenal.common import exception
# from arsenal.i18n import _
from arsenal.openstack.common import log as logging


LOG = logging.getLogger(__name__)


opts = [
    cfg.IntOpt('api_version',
               default=3,
               help='Version of Nova API service endpoint.'),
    cfg.StrOpt('api_endpoint',
               help='URL for Nova API endpoint.'),
    cfg.StrOpt('admin_username',
               help='Nova keystone admin name'),
    cfg.StrOpt('admin_password',
               help='Nova keystone admin password.'),
    cfg.StrOpt('admin_auth_token',
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
    ]

nova_group = cfg.OptGroup(name='nova',
                          title='Nova Options')

CONF = cfg.CONF
CONF.register_group(nova_group)
CONF.register_opts(opts, nova_group)


class NovaClientWrapper(object):
    """Nova client wrapper class that encapsulates retry logic."""

    def __init__(self):
        """Initialise the NovaClientWrapper for use."""
        self._cached_client = None

    def _invalidate_cached_client(self):
        """Tell the wrapper to invalidate the cached nova-client."""
        self._cached_client = None

    def _get_client(self):
        # If we've already constructed a valid, authed client, just return
        # that.
        if self._cached_client is not None:
            return self._cached_client

        auth_token = CONF.nova.admin_auth_token
        if auth_token is None:
            kwargs = {'username': CONF.nova.admin_username,
                      'password': CONF.nova.admin_password,
                      'auth_url': CONF.nova.admin_url,
                      'tenant_name': CONF.nova.admin_tenant_name,
                      'service_type': 'compute',
                      'endpoint_type': 'public'}
        else:
            kwargs = {'auth_token': auth_token,
                      'auth_url': CONF.nova.admin_url}

        try:
            cli = client.Client(CONF.nova.api_version, **kwargs)
            # Cache the client so we don't have to reconstruct and
            # reauthenticate it every time we need it.
            self._cached_client = cli

        except nova_exc.Unauthorized:
            msg = "Unable to authenticate Nova client."
            LOG.error(msg)
            raise exception.ArsenalException(msg)

        return cli

    def _multi_getattr(self, obj, attr):
        """Support nested attribute path for getattr().

        :param obj: Root object.
        :param attr: Path of final attribute to get. E.g., "a.b.c.d"

        :returns: The value of the final named attribute.
        :raises: AttributeError will be raised if the path is invalid.
        """
        for attribute in attr.split("."):
            obj = getattr(obj, attribute)
        return obj

    def call(self, method, *args, **kwargs):
        """Call an Nova client method and retry on errors.

        :param method: Name of the client method to call as a string.
        :param args: Client method arguments.
        :param kwargs: Client method keyword arguments.

        :raises: ArsenalException if all retries failed.
        """
        retry_excs = (nova_exc.ConnectionRefused,
                      nova_exc.Conflict)
        num_attempts = CONF.nova.api_max_retries

        for attempt in range(1, num_attempts + 1):
            client = self._get_client()

            try:
                return self._multi_getattr(client, method)(*args, **kwargs)
            except nova_exc.Unauthorized:
                # In this case, the authorization token of the cached
                # nova-client probably expired. So invalidate the cached
                # client and the next try will start with a fresh one.
                self._invalidate_cached_client()
                LOG.debug("The Nova client became unauthorized. "
                          "Will attempt to reauthorize and try again.")
            except retry_excs:
                pass

            # We want to perform this logic for all exception cases listed
            # above.
            msg = ("Error contacting Nova server for "
                   "'%(method)s'. Attempt %(attempt)d of %(total)d" %
                   {'method': method,
                    'attempt': attempt,
                    'total': num_attempts})
            if attempt == num_attempts:
                LOG.error(msg)
                raise exception.ArsenalException(msg)
            LOG.warning(msg)
            time.sleep(CONF.nova.api_retry_interval)
