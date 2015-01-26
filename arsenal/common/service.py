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

from oslo.config import cfg

from arsenal.common import config
from arsenal.openstack.common import service


class ArsenalService(service.Service):
    def __init__(self):
        super(ArsenalService, self).__init__()

    def start(self):
        super(ArsenalService, self).start()

    def stop(self):
        super(ArsenalService, self).stop()

def prepare_service(argv=[]):
    config.parse_args(argv)
    # TODO: Setup defaults.
    # log.setup('arsenal')
