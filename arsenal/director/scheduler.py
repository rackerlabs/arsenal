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

from arsenal.director import scout
from arsenal.openstack.common import log
from arsenal.openstack.common import periodic_task
from arsenal.strategy import base as sb

LOG = log.getLogger(__name__)

CONF = cfg.CONF


class DirectorScheduler(periodic_task.PeriodicTasks):
    """Arsenal Director Scheduler class."""

    def __init__(self):
        super(DirectorScheduler, self).__init__()
        self.node_data = []
        self.image_data = []
        self.flavor_data = []
        self.strat = sb.get_configured_strategy()
        self.scout = scout.Scout()

    def periodic_tasks(self, context, raise_on_error=False):
        return self.run_periodic_tasks(context, raise_on_error)

    @periodic_task.periodic_task
    def update_strategy(self, context):
        self.strat.update_current_state(self.node_data, self.image_data,
                                        self.flavor_data)

    @periodic_task.periodic_task
    def get_directives(self, context):
        self.directives = self.strat.directives()

    @periodic_task.periodic_task
    def poll_for_node_data(self, context):
        self.node_data = self.scout.retrieve_node_data()

    @periodic_task.periodic_task
    def poll_for_flavor_data(self, context):
        self.node_data = self.scout.retrieve_flavor_data()

    @periodic_task.periodic_task
    def poll_for_image_data(self, context):
        self.node_data = self.scout.retrieve_image_data()
