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

import abc
import time
import types

from oslo.config import cfg
import six

from arsenal.common import exception
from arsenal.openstack.common import log as logging


LOG = logging.getLogger(__name__)


opts = [
    cfg.StrOpt('os_username',
               help='Openstack keystone admin name'),
    cfg.StrOpt('os_password',
               secret=True,
               help='Openstack keystone admin password.'),
    cfg.StrOpt('os_auth_token',
               secret=True,
               help='Openstack keystone auth token.'),
    cfg.StrOpt('os_api_url',
               help='Keystone public API endpoint.'),
    cfg.StrOpt('os_tenant_name',
               help='Openstack keystone tenant name.'),
    cfg.StrOpt('os_tenant_id',
               help='Openstack keystone tenant ID.'),
    cfg.IntOpt('call_max_retries',
               default=60,
               help='How many times to retry a call when the call fails in '
                    'some recoverable way.'),
    cfg.IntOpt('call_retry_interval',
               default=2,
               help='How often to retry in seconds when a request '
                    'fails in some recoverable way.'),
    cfg.StrOpt('region_name',
               help='Openstack region name.'),
    cfg.StrOpt('service_name',
               help='Openstack service name.'),
    cfg.StrOpt('auth_system',
               default='keystone',
               help='Openstack auth_system argument.'),
]

client_wrapper_group = cfg.OptGroup(name='client_wrapper',
                                    title='Configuration for the Openstack '
                                          'client wrapper.')

CONF = cfg.CONF
CONF.register_group(client_wrapper_group)
CONF.register_opts(opts, client_wrapper_group)


def first_not_none(iterable):
    """Select the first item from an iterable that is not None.

    The idea is that you can use this to specify a list of fall-backs to use
    for configuration options.
    """
    for item in iterable:
        if item is not None:
            return item
    return None


@six.add_metaclass(abc.ABCMeta)
class OpenstackClientWrapper(object):
    """An abstract interface for wrapping an Openstack client.

        """
    def __init__(self,
                 retry_exceptions,
                 auth_exceptions,
                 name="Openstack"):
        """Initialise the OpenstackClientWrapper for use.

        :param retry_exceptions: A tuple of default client exceptions which
            should cause the call method to be retried.
        :param auth_exceptions: A tuple of default client exceptions which
            should cause the call method wrapper to attempt to reauthorize the
            client.
        :param name: The name of the client.
        """
        self._cached_client = None
        self.name = name
        self.retry_exceptions = retry_exceptions
        self.auth_exceptions = auth_exceptions

    def _invalidate_cached_client(self):
        """Tell the wrapper to invalidate the cached client."""
        self._cached_client = None

    @abc.abstractmethod
    def _get_new_client(self):
        """Provides an abstract way to access the wrapped client."""
        pass

    def _get_client(self):
        """Gets the wrapped client."""
        if self._cached_client is None:
            self._cached_client = self._get_new_client()
        return self._cached_client

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

    def call(self, method_name, *args, **kwargs):
        """Call the specified client method and retry on errors.

        :param method_name: Name of the client method to call as a string.
        :param args: Client method arguments.
        :param kwargs: Client method keyword arguments.

        :raises: ArsenalException if all retries failed.
        """
        retry_exceptions = self.retry_exceptions
        auth_exceptions = self.auth_exceptions
        max_retries = CONF.client_wrapper.call_max_retries
        retry_interval = CONF.client_wrapper.call_retry_interval

        for attempt in range(1, max_retries + 1):
            client = self._get_client()

            try:
                result = self._multi_getattr(client, method_name)(*args,
                                                                  **kwargs)
                # NOTE(ClifHouck): If the return type is a generator,
                # then force the generator to unwind, because otherwise we
                # won't get the wrapping behavior this method provides.
                # FIXME(ClifHouck): Instead of forcing a complete unwind,
                # wrap the generator with our own, which provides individually
                # wrapped calls, and return that.
                if isinstance(result, types.GeneratorType):
                    gen_list = []
                    for r in result:
                        gen_list.append(r)
                    return gen_list

                return result
            except auth_exceptions:
                # In this case, the authorization token of the cached
                # client probably expired. So invalidate the cached
                # client and the next try will start with a fresh one.
                self._invalidate_cached_client()
                LOG.debug("The wrapped %(name)s client became unauthorized. "
                          "Will attempt to reauthorize and try again." % {
                              'name': self.name})
            except retry_exceptions as e:
                LOG.debug("Got a retry-able exception." + str(e))
                pass

            # We want to perform this logic for all exception cases listed
            # above.
            msg = ("Error contacting %(name)s server for "
                   "'%(method)s'. Attempt %(attempt)d of %(total)d" %
                   {'name': self.name,
                    'method': method_name,
                    'attempt': attempt,
                    'total': max_retries})
            if attempt == max_retries:
                LOG.error(msg)
                raise exception.ArsenalException(msg)
            LOG.warning(msg)
            time.sleep(retry_interval)
