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

from arsenal.openstack.common import log
from arsenal.openstack.common import periodic_task

LOG = log.getLogger(__name__)

CONF = cfg.CONF


class DirectorScheduler(periodic_task.PeriodicTasks):
    """Arsenal Director Scheduler class."""

    def __init__(self):
        super(DirectorScheduler, self).__init__()

    def periodic_tasks(self, context, raise_on_error=False):
        return self.run_periodic_tasks(context, raise_on_error)

    @periodic_task.periodic_task
    def _poll_for_unprovisioned_ironic_nodes(self, context):
        LOG.info("DirectorScheduler._poll_for_unprovisioned_ironic_nodes: "
                 "Beginning poll...")
        LOG.info("DirectorScheduler._poll_for_unprovisioned_ironic_nodes: "
                 "Finished!")
