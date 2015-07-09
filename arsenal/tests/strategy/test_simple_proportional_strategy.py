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

from __future__ import division
import random

from oslo_config import cfg

from arsenal.strategy import base as sb
from arsenal.strategy import simple_proportional_strategy as sps
from arsenal.tests import base as test_base
from arsenal.tests.strategy import test_strategy_base as sb_test

CONF = cfg.CONF

INVALID_IMAGE = sb.ImageInput("Windows95", "abcd", "uvwx")


class TestSimpleProportionalStrategy(test_base.TestCase):

    def setUp(self):
        super(TestSimpleProportionalStrategy, self).setUp()
        # Setup a few simple cases, that are mostly defaults.
        self.environments = {
            'one_unprovisioned_node_environment': {
                'nodes': [sb.NodeInput("caaa", "Compute", False, False, None)],
            },
            'one_provisioned_node_environment': {
                'nodes': [sb.NodeInput("caaa", "Compute", True, False, None)],
            },
            'two_node_environment': {
                'nodes': [
                    sb.NodeInput("caaa", "Compute", False, False, None),
                    sb.NodeInput("cbbb", "Compute", False, False, None),
                ],
            }
        }

        # Some programmatically constructed. With random provision and
        # cached states. Also, some nodes will have invalid images.
        node_counts = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
        flavors = ["IO", "Compute", "Memory"]
        images_with_invalid = []
        images_with_invalid.extend(sb_test.TEST_IMAGES)
        images_with_invalid.append(INVALID_IMAGE)
        for n_count in node_counts:
            print("Building random nodes for random-nodes(%d)" % n_count)
            environment = {'nodes': []}
            for n in range(n_count):
                flavor_pick = random.choice(flavors)
                image_pick_uuid = random.choice(images_with_invalid).uuid
                provisioned_choice = random.choice([False, True])

                cache_choice = False
                if not provisioned_choice:
                    cache_choice = random.choice([False, True])

                environment['nodes'].append(
                    sb.NodeInput("%s-%d" % (flavor_pick[0], n),
                                 flavor_pick,
                                 provisioned_choice,
                                 cache_choice,
                                 image_pick_uuid))
                print(str(environment['nodes'][-1]))
            self.environments["random-nodes(%d)" % n_count] = environment

        # Defaults
        for env_name, env_dict in self.environments.iteritems():
            env_dict['flavors'] = sb_test.TEST_FLAVORS
            env_dict['images'] = sb_test.TEST_IMAGES

    def test_proportion_goal_versus_several_percentages(self):
        print("Starting test_proportion_goal_versus_several_percentages.")
        percentages = [0, 0.1, 0.25, 0.50, 0.75, 0.90, 1]
        for percent in percentages:
            print("Trying %d percent." % percent)
            self._test_proportion_goal_versus_environment(percent)

    def _test_proportion_goal_versus_environment(self, test_percentage=0.50):
        """Test that strategy goals are always being met by directives output.
        Are we always caching at least enough to hit our proportion goal.
        """
        CONF.set_override('percentage_to_cache',
                          test_percentage,
                          group='simple_proportional_strategy')
        strategy = sps.SimpleProportionalStrategy()
        for env_name, env in self.environments.iteritems():
            print("Testing %s environment." % env_name)
            strategy.update_current_state(**env)
            directives = strategy.directives()
            print("Directives:")
            if directives:
                for directive in directives:
                    print(str(directive))
            for flavor in env['flavors']:
                self._test_proportion_goal_versus_flavor(
                    strategy, directives, env['nodes'], flavor)

    def _test_proportion_goal_versus_flavor(self, strat, directives, nodes,
                                            flavor):
        print("Testing flavor %s." % flavor.name)
        flavor_nodes = filter(lambda node: flavor.is_flavor_node(node), nodes)
        unprovisioned_node_count = len(sps.unprovisioned_nodes(flavor_nodes))
        available_node_count = len(sps.nodes_available_for_caching(
            flavor_nodes))
        cached_node_count = len(filter(lambda node: node.cached, flavor_nodes))
        if directives:
            cache_directive_count = len(
                filter(
                    lambda directive: (
                        isinstance(directive, sb.CacheNode) and
                        flavor.is_flavor_node(sb.NodeInput(directive.node_uuid,
                                                           '?'))),
                    directives))
        else:
            cache_directive_count = 0
        self.assertTrue(
            cache_directive_count <= available_node_count,
            ("There shouldn't be more cache directives than "
             "there are nodes available to cache."))

        total_percent_cached = 0
        if unprovisioned_node_count != 0 and available_node_count != 0:
            total_percent_cached = (
                cache_directive_count + cached_node_count) / (
                unprovisioned_node_count)
            # This handles the fact that SimpleProportionalStrategy floors
            # the number of nodes to cache, so we don't always cache a node
            # if there's only a fractional node to cache.
            total_percent_cached += (1 / unprovisioned_node_count)
            self.assertTrue((
                total_percent_cached >= strat.percentage_to_cache), (
                    "The number of cache directives emitted by the "
                    "strategy does not fulfill the goal! Total percent to "
                    "be cached: %f, expected %f" % (
                        total_percent_cached, strat.percentage_to_cache)))
        else:
            self.assertTrue(cache_directive_count == 0, (
                "Since there are no available nodes to cache, the number "
                "of cache directives should be zero, but got %d" % (
                    cache_directive_count)))

    def test_dont_eject_provisioned_nodes(self):
        """Don't try to eject nodes which are considered provisioned."""
        strategy = sps.SimpleProportionalStrategy()
        invalid_cached_and_provisioned_node = {
            'nodes': [sb.NodeInput("caaa", "Compute", True, True,
                                   INVALID_IMAGE)],
            'flavors': sb_test.TEST_FLAVORS,
            'images': sb_test.TEST_IMAGES
        }
        strategy.update_current_state(**invalid_cached_and_provisioned_node)
        directives = strategy.directives()
        self.assertTrue(len(directives) == 0,
                        "Trying to eject a provisioned node!")

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
            directives or [sb.CacheNode('a', 'b', 'c')])
        ejected_node_uuids = sb.build_attribute_set(ejection_directives,
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
        valid_percentages = [0, 0.01, 0.025, 0.05011, 0.1, 0.15, 0.9999, 1]
        invalid_percentages = [-1, -5, -0.1, 1.001, 1.00001]
        for percentage in valid_percentages:
            CONF.set_override('percentage_to_cache',
                              percentage,
                              group='simple_proportional_strategy')
            try:
                sps.SimpleProportionalStrategy()
            except sps.InvalidPercentageError:
                self.assertTrue(False, (
                    "SimpleProportionalStrategy raised InvalidPercentageError "
                    "for %f inappropriately." % (percentage)))

        for percentage in invalid_percentages:
            CONF.set_override('percentage_to_cache',
                              percentage,
                              group='simple_proportional_strategy')
            self.assertRaises(sps.InvalidPercentageError,
                              sps.SimpleProportionalStrategy)
