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

from arsenal.tests.functional import base as test_base


class TestArsenalFunctional(test_base.TestCase):

    def setUp(self):
        """
        Set the endpoints for ironic and glance.
        """
        super(TestArsenalFunctional, self).setUp()

    def tearDown(self):
        """
        Kill the arsenal and mimic services
        """
        super(TestArsenalFunctional, self).tearDown()

    def test_arsenal_dry_run(self):
        """
        Arsenal does not cache images when dry run is set to True
        """
        # create arsenal config with dry_run=True
        config_file = self.generate_config_file_name()
        config_values = self.set_config_values(dry_run=True)
        self.create_arsenal_config_file(config_values, file_name=config_file)

        # start mimic
        self.start_mimic_service()

        # start arsenal
        self.start_arsenal_service(config_file=config_file)

        # verify no nodes were cached
        after = self.get_cached_ironic_nodes()
        self.assertEqual(len(after), 0)

    def test_arsenal_does_not_cache_provisioned_nodes(self):
        """
        Arsenal does not cache image when all the nodes are provisioned
        """
        # start mimic and get provisioned nodes before starting arsenal
        # verify that they were not cached
        self.start_mimic_service()
        get_provisioned_nodes_before = self.get_ironic_nodes(provisioned=True)
        for each_provisioned_node in get_provisioned_nodes_before:
            self.assertFalse(each_provisioned_node['driver_info'].get('cache_image_id'))

        # start arsenal and verify the provisioned nodes do not change
        self.start_arsenal_service(config_file=self.default_config_file)
        get_provisioned_nodes_after = self.get_ironic_nodes(provisioned=True)
        self.assertEqual(get_provisioned_nodes_before, get_provisioned_nodes_after)

    def test_arsenal_caches_nodes_per_given_percentage_1(self):
        """
        Given percentage 30%, arsenal caches only half the nodes available
        """
        # create arsenal config with percentage_to_cache=0.3
        config_file = self.generate_config_file_name()
        config_values = self.set_config_values(percentage_to_cache=0.3)
        self.create_arsenal_config_file(config_values, file_name=config_file)

        # start mimic and get nodes avaiable not already provisioned
        self.start_mimic_service()
        before = self.get_ironic_nodes()

        # start arsenal and verify the unprovisioned node count remains the same
        self.start_arsenal_service(config_file=config_file,
                                   service_status="Got 0 cache directives from the strategy")
        after = self.get_ironic_nodes()
        self.assertEqual(len(before), len(after))

        # get list of cached nodes and verify that it is 30% of available nodes
        cached_nodes = self.get_cached_ironic_nodes()
        expected_cached_nodes = self.calculate_percentage_to_be_cached(len(after), 0.3)
        self.assertEqual(len(cached_nodes), expected_cached_nodes)

    def test_arsenal_caches_nodes_per_given_percentage_2(self):
        """
        Given percentage 100%, arsenal caches only half the nodes available
        """
        # create arsenal config with percentage_to_cache=0.25
        config_file = self.generate_config_file_name()
        config_values = self.set_config_values(percentage_to_cache=0.25)
        self.create_arsenal_config_file(config_values, file_name=config_file)

        # start mimic and get nodes avaiable not already provisioned
        self.start_mimic_service()
        before = self.get_ironic_nodes()

        # start arsenal and verify the unprovisioned node count remains the same
        self.start_arsenal_service(config_file=config_file,
                                   service_status="Got 0 cache directives from the strategy")
        after = self.get_ironic_nodes()
        self.assertEqual(len(before), len(after))

        # get list of cached nodes and verify that it is 100% of available nodes
        cached_nodes = self.get_cached_ironic_nodes()
        expected_cached_nodes = self.calculate_percentage_to_be_cached(len(after), 0.25)
        self.assertEqual(len(cached_nodes), expected_cached_nodes)

    # def test_arsenal_caches_only_weighted_images(self):
    #     """
    #     When only one image is listed in the image_weight in the config,
    #     arsenal only caches that image on all nodes.
    #     """
    #     image_weight = {'OnMetal - CentOS 6': 100}
    #     # create arsenal config with dry_run=True
    #     config_file = self.generate_config_file_name()
    #     config_values = self.set_config_values(image_weights=image_weight,
    #                                            percentage_to_cache=1)
    #     self.create_arsenal_config_file(config_values, file_name=config_file)

    #     # start mimic
    #     self.start_mimic_service()
    #     before = self.get_ironic_nodes()

    #     # start arsenal
    #     self.start_arsenal_service(config_file=config_file)

    #     # get list of cached nodes and verify that it is 100% of available nodes
    #     # are cached with the image listed in image_weights
    #     cached_nodes = self.get_cached_ironic_nodes()
    #     self.assertEqual(len(cached_nodes), len(before))
    #     nodes_per_image = self.list_ironic_nodes_by_image(cached_nodes, count=True)
    #     self.assertEqual(nodes_per_image['OnMetal - CentOS 6'], len(before))

    # def test_arsenal_caches_per_assigned_images_weights(self):
    #     """
    #     Arsenal caches images with maximum weights the most and vice versa
    #     FAIL: Node not cached per image weights
    #     """
    #     # start mimic
    #     self.start_mimic_service()
    #     before = self.get_ironic_nodes()

    #     # start arsenal
    #     self.start_arsenal_service(config_file=self.default_config_file)

    #     # get list of cached nodes and verify that images with the most weight are
    #     # cached the most
    #     cached_nodes = self.get_cached_ironic_nodes()
    #     nodes_per_image = self.list_ironic_nodes_by_image(cached_nodes, count=True)
    #     self.assertTrue(nodes_per_image['OnMetal - Ubuntu 14.04 LTS (Trusty Tahr)'] < len(before))
    #     self.assertTrue(nodes_per_image['OnMetal - Ubuntu 14.04 LTS (Trusty Tahr)'] >
    #                     nodes_per_image['OnMetal - CoreOS (Beta)'])

    def test_arsenal_ejects_images(self):
        """
        Arsenal ejects images when an images are out of date
        """
        pass

    def test_arsenal_ejects_images_fails(self):
        """
        Arsenal ejects images when an images are out of date, but all cached nodes
        are already provisioned
        """
        pass

    def test_arsenal_caching_when_new_nodes_are_added(self):
        """
        Arsenal re-caches nodes when new nodes are added
        """
        pass

    def test_arsenal_caching_when_cached_nodes_are_deleted(self):
        """
        Arsenal re-caches nodes when cached nodes are deleted
        """
        pass
