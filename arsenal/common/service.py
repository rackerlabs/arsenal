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

import logging

from oslo.config import cfg

from arsenal.common import config
from arsenal.openstack.common import log
from arsenal.openstack.common import service

LOG = log.getLogger(__name__)


class ArsenalService(service.Service):
    def __init__(self):
        super(ArsenalService, self).__init__()
        # Delaying import of the scheduler until after the configuration
        # options are handled in prepare_service.
        from arsenal.director import scheduler
        self.scheduler = scheduler.DirectorScheduler()

    def start(self):
        LOG.info('Starting Arsenal service with the following options:')
        cfg.CONF.log_opt_values(LOG, logging.INFO)
        super(ArsenalService, self).start()
        LOG.info('Started Arsenal service.')
        self.tg.add_dynamic_timer(self.scheduler.periodic_tasks, context={})

    def stop(self):
        super(ArsenalService, self).stop(graceful=True)
        LOG.info('Stopped Arsenal service.')


def prepare_service(argv=[]):
    config.parse_args(argv)
    log.setup('arsenal')
