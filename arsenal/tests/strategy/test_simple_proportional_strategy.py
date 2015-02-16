# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
test_SimpleProportionalStrategy
----------------------------------

Test the simple proportional caching strategy to determine whether its
behavior appears to be correct.
"""

import random

from arsenal.strategy import base as sb
from arsenal.strategy import simple_proportional_strategy as sps
from arsenal.tests import base as test_base


def name_starts_with(node, letter):
    return node.node_uuid[0] == letter


TEST_FLAVORS = [
    sb.FlavorInput("IO", lambda node: name_starts_with(node, 'i')),
    sb.FlavorInput("Compute", lambda node: name_starts_with(node, 'c')),
    sb.FlavorInput("Memory", lambda node: name_starts_with(node, 'm')),
]

TEST_IMAGES = [
    sb.ImageInput("Ubuntu", "aaaa"),
    sb.ImageInput("CentOS", "bbbb"),
    sb.ImageInput("CoreOS", "cccc"),
    sb.ImageInput("Redhat", "dddd"),
    sb.ImageInput("Windows", "eeee")
]

INVALID_IMAGE = sb.ImageInput("Windows95", "abcd")


class TestSimpleProportionalStrategy(test_base.TestCase):

    def setUp(self):
        super(TestSimpleProportionalStrategy, self).setUp()
        # Setup a few simple cases, that are mostly defaults.
        self.environments = {
            'one_unprovisioned_node_environment': {
                'nodes': [sb.NodeInput("caaa", False, False, None)],
            },
            'one_provisioned_node_environment': {
                'nodes': [sb.NodeInput("caaa", True, False, None)],
            },
            'two_node_environment': {
                'nodes': [
                    sb.NodeInput("caaa", False, False, None),
                    sb.NodeInput("cbbb", False, False, None),
                ],
            }
        }

        # Some programmatically constructed. With random provision and
        # cached states. Also, some nodes will have invalid images.
        node_counts = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
        flavor_prefixes = ['i', 'c', 'm']
        images_with_invalid = []
        images_with_invalid.extend(TEST_IMAGES)
        images_with_invalid.append(INVALID_IMAGE)
        for n_count in node_counts:
            environment = {'nodes': []}
            for n in range(n_count):
                flavor_pick = random.choice(flavor_prefixes)
                image_pick_uuid = random.choice(images_with_invalid).uuid
                environment['nodes'].append(
                    sb.NodeInput("%s-%d" % (flavor_pick, n),
                                 random.randint(0, 1),
                                 random.randint(0, 1),
                                 image_pick_uuid))
            self.environments["random-nodes(%d)" % n_count] = environment

        # Defaults
        for env_name, env_dict in self.environments.iteritems():
            env_dict['flavors'] = TEST_FLAVORS
            env_dict['images'] = TEST_IMAGES

    def test_proportion_goal_versus_several_percentages(self):
        print("Starting test_proportion_goal_versus_several_percentages.")
        percentages = [0, 10, 25, 50, 75, 90, 100]
        for percent in percentages:
            print("Trying %d percent." % percent)
            self._test_proportion_goal(percent)

    def _test_proportion_goal(self, test_percentage=50):
        """Test that strategy goals are always being met by directives output.
        Are we always caching at least enough to hit our proportion goal.
        """
        strategy = sps.SimpleProportionalStrategy(test_percentage)
        for env_name, env in self.environments.iteritems():
            print("Testing %s environment." % env_name)
            strategy.update_current_state(**env)
            directives = strategy.directives()
            available_node_count = len(sps.available_nodes(env['nodes']))
            cached_node_count = len(filter(lambda node: node.cached,
                                           env['nodes']))
            cache_directive_count = len(filter(
                lambda directive: isinstance(directive, sb.CacheNode),
                directives))
            self.assertTrue(cache_directive_count <= available_node_count,
                            ("There shouldn't be more cache directives than "
                             "there are nodes available to cache."))

            total_percent_cached = 0
            if available_node_count != 0:
                total_percent_cached = (
                    cache_directive_count + cached_node_count) / (
                    available_node_count)
                self.assertTrue((
                    total_percent_cached >= test_percentage / 100), (
                    "The number of cache directives emitted by the strategy "
                    "does not fulfill the goal! Total percent to be "
                    "cached: %f, expected %f" % (total_percent_cached,
                                                 test_percentage / 100)))
            else:
                self.assertTrue(cache_directive_count == 0, (
                    "Since there are no available nodes to cache, the number "
                    "of cache directives should be zero, but got %d" % (
                        cache_directive_count)))

    def test_node_ejection_behavior(self):
        """Perform the ejection test for all test environments."""
        for env_name, env in self.environments.iteritems():
            print("Testing ejection behavior for '%s'." % env_name)
            self._ejection_test(env)

    def _ejection_test(self, env):
        """Are we ejecting nodes whose images are no longer in the current
        image list?
        """
        strategy = sps.SimpleProportionalStrategy()
        strategy.update_current_state(**env)
        directives = strategy.directives()
        ejection_directives = filter(
            lambda direct: isinstance(direct, sb.EjectNode),
            directives)
        ejected_node_uuids = sps.build_attribute_set(ejection_directives,
                                                     'node_uuid')
        for node in env['nodes']:
            # Make sure that cached nodes with invalid images are ejected.
            if node.cached_image_uuid == INVALID_IMAGE.uuid and node.cached:
                self.assertIn(node.node_uuid,
                              ejected_node_uuids,
                              ("A node with an invalid image UUID was not "
                               "ejected from the cache. Node UUID: %s" % (
                                   node.node_uuid)))

    def test_percentage_clamp(self):
        """Make sure valid percentages are valid, and invalid percentages
        raise exceptions.
        """
        valid_percentages = [0, 1, 2.5, 5.011, 10, 15, 99.99, 100]
        invalid_percentages = [-1, -5, -0.1, 101, 100.001]
        for percentage in valid_percentages:
            try:
                sps.SimpleProportionalStrategy(percentage)
            except sps.InvalidPercentageError:
                self.assertTrue(False, (
                    "SimpleProportionalStrategy raised InvalidPercentageError "
                    "for %f inappropriately." % (percentage)))

        for percentage in invalid_percentages:
            self.assertRaises(sps.InvalidPercentageError,
                              sps.SimpleProportionalStrategy,
                              percentage)
