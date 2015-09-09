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
import time
import unittest

from arsenal.tests.functional import base as test_base


class TestArsenalFunctional(test_base.TestCase):

    def setUp(self):
        """Set the endpoints for ironic and glance."""
        super(TestArsenalFunctional, self).setUp()

    def tearDown(self):
        """Kill the arsenal and mimic services."""
        super(TestArsenalFunctional, self).tearDown()

    def test_arsenal_dry_run(self):
        """Arsenal does not cache images when dry run is set to True.
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
        """Arsenal does not cache image when all the nodes are
        provisioned.
        """
        # start mimic and get provisioned nodes before starting arsenal
        # verify that they were not cached
        self.start_mimic_service()
        get_provisioned_nodes_before = self.get_provisioned_ironic_nodes()
        for each_provisioned_node in get_provisioned_nodes_before:
            self.assertFalse(
                each_provisioned_node['driver_info'].get('cache_image_id'))

        # start arsenal and verify the provisioned nodes do not change
        self.start_arsenal_service()
        get_provisioned_nodes_after = self.get_provisioned_ironic_nodes()
        self.assertEqual(get_provisioned_nodes_before,
                         get_provisioned_nodes_after)


class TestArsenalStrategy(test_base.TestCase):

    def setUp(self):
        """Set the endpoints for ironic and glance."""
        super(TestArsenalStrategy, self).setUp()
        self.strategy = ("simple_proportional_strategy" +
                         ".SimpleProportionalStrategy")

    def tearDown(self):
        """Kill the arsenal and mimic services."""
        super(TestArsenalStrategy, self).tearDown()

    def test_arsenal_caches_nodes_per_given_percentage_1(self):
        """Given percentage 30%, arsenal caches only half the nodes
        available.
        """
        # create arsenal config with percentage_to_cache=0.3
        config_file = self.generate_config_file_name()
        config_values = self.set_config_values(percentage_to_cache=0.3)
        self.create_arsenal_config_file(config_values, file_name=config_file)

        # start mimic and get nodes available i.e. not already provisioned
        self.start_mimic_service()
        before = self.get_unprovisioned_ironic_nodes()

        # start arsenal and verify the unprovisioned node count is the same
        self.start_arsenal_service(
            config_file=config_file,
            service_status="Got 0 cache directives from the strategy")
        after = self.get_unprovisioned_ironic_nodes()
        self.assertEqual(len(before), len(after))

        # get list of cached nodes and verify that it is 30% of available nodes
        cached_nodes = self.get_cached_ironic_nodes()
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(after), 0.3)
        self.assertEqual(len(cached_nodes), expected_cached_nodes)

    def test_arsenal_caches_nodes_per_given_percentage_2(self):
        """Given percentage 25%, arsenal caches only 25 percent the nodes
        available.
        """
        # create arsenal config with percentage_to_cache=0.25
        config_file = self.generate_config_file_name()
        config_values = self.set_config_values(percentage_to_cache=0.25)
        self.create_arsenal_config_file(config_values, file_name=config_file)

        # start mimic and get nodes available i.e. not already provisioned
        self.start_mimic_service()
        before = self.get_unprovisioned_ironic_nodes()

        # start arsenal and verify the unprovisioned node count is the same
        self.start_arsenal_service(
            config_file=config_file,
            service_status="Got 0 cache directives from the strategy")
        after = self.get_unprovisioned_ironic_nodes()
        self.assertEqual(len(before), len(after))

        # get list of cached nodes and verify that its 25% of available nodes
        cached_nodes = self.get_cached_ironic_nodes()
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(after), 0.25)
        self.assertEqual(len(cached_nodes), expected_cached_nodes)

    def test_arsenal_caches_nodes_per_given_percentage_3(self):
        """Given percentage 100%, arsenal caches all the nodes
        available.
        """
        # create arsenal config with percentage_to_cache=0.1
        config_file = self.generate_config_file_name()
        config_values = self.set_config_values(percentage_to_cache=1)
        self.create_arsenal_config_file(config_values, file_name=config_file)

        # start mimic and get nodes available i.e. not already provisioned
        self.start_mimic_service()
        before = self.get_unprovisioned_ironic_nodes()

        # start arsenal and verify the unprovisioned node count is the same
        self.start_arsenal_service(
            config_file=config_file,
            service_status="Got 0 cache directives from the strategy")
        after = self.get_unprovisioned_ironic_nodes()
        self.assertEqual(len(before), len(after))

        # get list of cached nodes and verify that its 25% of available nodes
        cached_nodes = self.get_cached_ironic_nodes()
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(after), 1)
        self.assertEqual(len(cached_nodes), expected_cached_nodes)

    @unittest.skip("Issue: https://github.com/rackerlabs/arsenal/issues/61")
    def test_arsenal_caches_only_weighted_images(self):
        """When the image_weight for an image is set to 0,
        arsenal will not cache that image.
        """
        image_weight = {'OnMetal - CentOS 6': 0}

        # create arsenal config with image_weight set to 0 for one image
        config_file = self.generate_config_file_name()
        config_values = self.set_config_values(image_weights=image_weight,
                                               percentage_to_cache=1)
        self.create_arsenal_config_file(config_values, file_name=config_file)

        # start mimic
        self.start_mimic_service()
        before = self.get_unprovisioned_ironic_nodes()

        # start arsenal
        self.start_arsenal_service(
            config_file=config_file,
            service_status="Got 0 cache directives from the strategy")

        # get list of cached nodes and verify that it is 100% of available
        # nodes are cached without the image with image_weight as 0
        cached_nodes = self.get_cached_ironic_nodes()
        self.assertEqual(len(cached_nodes), len(before))
        nodes_per_image = self.list_ironic_nodes_by_image(cached_nodes,
                                                          count=True)
        self.assertFalse(nodes_per_image.get('OnMetal - CentOS 6'))

    @unittest.skip("Issue: https://github.com/rackerlabs/arsenal/issues/61")
    def test_arsenal_cache_when_default_image_weight_0(self):
        """When the default_image_weight is set to 0, arsenal will only cache
        the images with image_weight set to be greater than 0.
        """
        image_weight = {'OnMetal - CentOS 6': 120}

        # create arsenal config with image_weight set to 0 for one image
        config_file = self.generate_config_file_name()
        config_values = self.set_config_values(image_weights=image_weight,
                                               percentage_to_cache=1,
                                               default_image_weight=0)
        self.create_arsenal_config_file(config_values, file_name=config_file)

        # start mimic
        self.start_mimic_service()
        before = self.get_unprovisioned_ironic_nodes()

        # start arsenal
        self.start_arsenal_service(
            config_file=config_file,
            service_status="Got 0 cache directives from the strategy")

        # get list of cached nodes and verify that it is 100% of available
        # nodes are cached without the image with image_weight as 0
        cached_nodes = self.get_cached_ironic_nodes()
        self.assertEqual(len(cached_nodes), len(before))
        nodes_per_image = self.list_ironic_nodes_by_image(cached_nodes,
                                                          count=True)
        self.assertEqual(nodes_per_image.get('OnMetal - CentOS 6'),
                         len(before))

    @unittest.skip("Issue: https://github.com/rackerlabs/arsenal/issues/62")
    def test_arsenal_caches_per_assigned_images_weights(self):
        """Arsenal caches images with maximum weights the most and vice versa
        """
        # start mimic
        self.start_mimic_service()
        before = self.get_unprovisioned_ironic_nodes()

        # start arsenal
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")

        # get list of cached nodes and verify that images with the most
        # weight are cached the most
        cached_nodes = self.get_cached_ironic_nodes()
        nodes_per_image = self.list_ironic_nodes_by_image(cached_nodes,
                                                          count=True)
        self.assertTrue(
            nodes_per_image['OnMetal - Ubuntu 14.04 LTS (Trusty Tahr)'] <
            len(before))
        self.assertTrue(
            nodes_per_image['OnMetal - Ubuntu 14.04 LTS (Trusty Tahr)'] >
            nodes_per_image['OnMetal - CoreOS (Beta)'])

    def test_arsenal_caches_all_onmetal_images(self):
        """Arsenal caches all the onmetal images."""
        # start mimic
        self.start_mimic_service()

        # start arsenal and verify cached nodes are of all images
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        cached_nodes = self.get_cached_ironic_nodes()
        nodes_per_image = self.list_ironic_nodes_by_image(cached_nodes,
                                                          count=True)
        image_list = self.get_onmetal_images_names_from_mimic()
        self.assertEqual(sorted(image_list), sorted(nodes_per_image.keys()))

    def test_arsenal_ejects_images(self):
        """Arsenal ejects images when images are deleted."""
        # start mimic
        self.start_mimic_service()

        # start arsenal and verify cached nodes are of all images
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        unprovisioned_nodes = self.get_unprovisioned_ironic_nodes()
        images_before = self.get_onmetal_images_ids_from_mimic()

        # delete 2 of the cached images from mimic
        images_to_delete = images_before[:2]
        self.delete_image_from_mimic(images_to_delete)

        # verify the images were deleted successfully
        image_list_after = self.get_onmetal_images_ids_from_mimic()
        for each in images_to_delete:
            self.assertTrue(each not in image_list_after)
        self.assertEqual(len(images_before), len(image_list_after) + 2)

        self.wait_for_successful_recache()

        # verify the percentage_to_cache is still met
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(unprovisioned_nodes), 0.5)
        self.wait_for_cached_ironic_nodes(expected_cached_nodes)

    @unittest.skip("Feature not implemented yet.")
    def test_arsenal_cache_when_new_images_are_added(self):
        """Arsenal caches the newly added images based on the
        default_image_weight.
        """
        # start mimic
        self.start_mimic_service()

        # start arsenal and verify cached nodes are of all images
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        after = self.get_unprovisioned_ironic_nodes()
        cached_nodes_before = self.get_cached_ironic_nodes()
        nodes_per_image_before = self.list_ironic_nodes_by_image(
            cached_nodes_before,
            count=True)
        image_list_before = self.get_onmetal_images_names_from_mimic()
        self.assertEqual(sorted(image_list_before),
                         sorted(nodes_per_image_before.keys()))

        # Add a new onmetal image to Mimic
        new_image = [{"name": "OnMetal - Debian Testing (Stretch)",
                      "distro": "linux"}]
        self.add_new_image_to_mimic(new_image)

        # verify the new image was added successfully
        image_list_after = self.get_onmetal_images_names_from_mimic()
        self.assertEqual(len(image_list_before) + 1, len(image_list_after))

        self.wait_for_successful_recache()

        # verify the percentage_to_cache is still met
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(after), 0.5)
        self.wait_for_cached_ironic_nodes(expected_cached_nodes)

    def test_arsenal_cache_when_images_are_replaced(self):
        """Arsenal caches the images that have been replaced.
        """
        # start mimic
        self.start_mimic_service()

        # start arsenal and verify cached nodes are of all images
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        unprovisioned_nodes = self.get_unprovisioned_ironic_nodes()
        cached_nodes_before = self.get_cached_ironic_nodes()
        nodes_per_image_before = self.list_ironic_nodes_by_image(
            cached_nodes_before,
            count=True)
        image_list_before = self.get_onmetal_images_ids_from_mimic()
        self.assertEqual(sorted(self.get_onmetal_images_names_from_mimic()),
                         sorted(nodes_per_image_before.keys()))

        # Replace an existing image with Debian Testing (Stretch)
        new_image = [{"name": "OnMetal - Debian Testing (Stretch)",
                      "distro": "linux"}]
        self.add_new_image_to_mimic(new_image)
        images_to_delete = image_list_before[:1]
        self.delete_image_from_mimic(images_to_delete)

        # verify the cached images are only the images available after
        # the image replacement
        self.wait_for_successful_recache()

        # verify the percentage_to_cache is still met
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(unprovisioned_nodes), 0.5)
        self.wait_for_cached_ironic_nodes(expected_cached_nodes)

    def test_arsenal_caching_when_new_nodes_are_added(self):
        """Arsenal re-caches nodes when new nodes are added."""
        # start mimic
        self.start_mimic_service()
        before = self.get_unprovisioned_ironic_nodes()

        # start arsenal and verify cached nodes
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        after = self.get_unprovisioned_ironic_nodes()
        self.assertEqual(len(before), len(after))
        cached_nodes = self.get_cached_ironic_nodes()
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(after), 0.5)
        self.assertEqual(len(cached_nodes), expected_cached_nodes)

        # add 8 new nodes of the onmetal-io1 flavor
        self.add_new_nodes_to_mimic(8)
        after_adding_new_nodes = self.get_unprovisioned_ironic_nodes()
        self.assertEqual(len(after) + 8, len(after_adding_new_nodes))

        # verify cached nodes count upon re-cache
        newly_cached = self.calculate_percentage_to_be_cached(
            8, 0.5, by_flavor=False)
        expected_re_cached_nodes = newly_cached + expected_cached_nodes
        self.wait_for_cached_ironic_nodes(expected_re_cached_nodes)

    def test_arsenal_caching_when_cached_nodes_are_deleted(self):
        """Arsenal re-caches nodes when cached nodes are deleted."""
        # start mimic and add 10 onmetal-io flavor nodes
        self.start_mimic_service()
        self.add_new_nodes_to_mimic(10)
        before = self.get_unprovisioned_ironic_nodes()
        self.assertEqual(len(before), 10)

        # start arsenal and verify cached nodes
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        after = self.get_unprovisioned_ironic_nodes()
        cached_nodes = self.get_cached_ironic_nodes()
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(after), 0.5, by_flavor=False)
        self.assertEqual(len(cached_nodes), expected_cached_nodes)

        # delete all the cached nodes on mimic
        self.delete_cached_nodes_on_mimic(expected_cached_nodes)

        # verify cached nodes count upon re-cache
        re_cached_nodes = self.calculate_percentage_to_be_cached(
            (len(before) - expected_cached_nodes), 0.5, by_flavor=False)
        # expected_re_cached_nodes = newly_cached + expected_cached_nodes
        self.wait_for_cached_ironic_nodes(re_cached_nodes)

    def test_arsenal_caching_when_uncached_nodes_are_deleted(self):
        """Arsenal does not re-cache nodes when the cached nodes
        has met or is greater than the percentage_to_cache.
        """
        # start mimic and add 10 onmetal-io flavor nodes
        self.start_mimic_service()
        self.add_new_nodes_to_mimic(10)
        before = self.get_unprovisioned_ironic_nodes()
        self.assertEqual(len(before), 10)

        # start arsenal and verify cached nodes
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        after = self.get_unprovisioned_ironic_nodes()
        cached_nodes = self.get_cached_ironic_nodes()
        expected_cached_nodes = self.calculate_percentage_to_be_cached(
            len(after), 0.5, by_flavor=False)
        self.assertEqual(len(cached_nodes), expected_cached_nodes)

        # delete all the uncached nodes on mimic
        uncached_nodes = len(after) - expected_cached_nodes
        self.delete_cached_nodes_on_mimic(uncached_nodes, cached=False)

        # verify cached nodes count remains as is, as the percentage_to_cache
        # has already been met.
        self.wait_for_cached_ironic_nodes(expected_cached_nodes)

    def test_arsenal_ejects_images_when_nodes_already_provisioned(self):
        """Arsenal does not eject nodes when images are deleted, but all
        cached nodes are already provisioned.
        """
        # start mimic
        self.start_mimic_service()

        # start arsenal and verify cached nodes are of all images
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        provisioned_nodes = self.get_provisioned_ironic_nodes()

        # get cached nodes list and provision them to be 'active'
        cached_nodes_before = self.get_cached_ironic_nodes()
        node_list = [node['uuid'] for node in cached_nodes_before]
        self.set_provision_state(node_list, 'active')
        self.assertEqual(len(self.get_provisioned_ironic_nodes()),
                         len(node_list) + len(provisioned_nodes))

        # Delete all but one image
        image_list = self.get_onmetal_images_ids_from_mimic()
        self.delete_image_from_mimic(image_list[:len(image_list) - 1])
        self.assertEqual(len(self.get_onmetal_images_ids_from_mimic()), 1)

        self.wait_for_successful_recache()

    @unittest.skip('Fails: Only a subset of the images are cached')
    def test_arsenal_caching_when_nodes_are_provisioned(self):
        """Arsenal caches the unprovisioned nodes when all the
        cached images are provisioned.
        """
        # start mimic
        self.start_mimic_service()

        # start arsenal and verify cached nodes are of all images
        self.start_arsenal_service(
            service_status="Got 0 cache directives from the strategy")
        provisioned_nodes = self.get_provisioned_ironic_nodes()
        uncached_unprov_nodes = self.get_uncached_unprovisioned_ironic_nodes()

        # get cached nodes list and provision them to be 'active'
        cached_nodes_before = self.get_cached_ironic_nodes()
        node_list = [node['uuid'] for node in cached_nodes_before]
        self.set_provision_state(node_list, 'active')
        self.assertEqual(len(self.get_provisioned_ironic_nodes()),
                         len(node_list) + len(provisioned_nodes))

        # wait for nodes to re-cached
        newly_cached = self.calculate_percentage_to_be_cached(
            len(uncached_unprov_nodes), 0.5)
        self.wait_for_cached_ironic_nodes(
            newly_cached + len(cached_nodes_before))

        # verify the unprovisioned node are cached across images
        newly_cached_nodes = self.list_ironic_nodes_by_image(
            self.get_cached_unprovisioned_ironic_nodes(),
            count=True)
        self.assertTrue
        image_list_after_delete = self.get_onmetal_images_names_from_mimic()
        self.assertEqual(sorted(image_list_after_delete),
                         sorted(newly_cached_nodes.keys()))
