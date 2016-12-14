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
test_strategy_base
----------------------------------

Exposes tests which exercise functionality provided by arsenal.strategy.base.
"""

from __future__ import division
import collections
import copy
import json
import math
import os.path
import random
import tempfile

import mock
from oslo_config import cfg
import six

from arsenal.strategy import base as sb
from arsenal.tests.unit import base as test_base

CONF = cfg.CONF


def name_starts_with(node, letter):
    return node.node_uuid[0] == letter

TEST_FLAVORS = [
    sb.FlavorInput("IO", lambda node: name_starts_with(node, 'I')),
    sb.FlavorInput("Compute", lambda node: name_starts_with(node, 'C')),
    sb.FlavorInput("Memory", lambda node: name_starts_with(node, 'M')),
]

TEST_IMAGES = [
    sb.ImageInput("Ubuntu", "aaaa", "abcd"),
    sb.ImageInput("CentOS", "bbbb", "efgh"),
    sb.ImageInput("CoreOS", "cccc", "ijkl"),
    sb.ImageInput("Redhat", "dddd", "mnop"),
    sb.ImageInput("Windows", "eeee", "qrst")
]


class TestStrategyBase(test_base.TestCase):

    def setUp(self):
        super(TestStrategyBase, self).setUp()

    def test_find_image_differences_no_difference(self):
        empty_diff_dict = {'new': set(), 'changed': set(), 'retired': set()}
        self.assertEqual(empty_diff_dict,
                         sb.find_image_differences([], []))
        self.assertEqual(empty_diff_dict,
                         sb.find_image_differences(TEST_IMAGES, TEST_IMAGES))

    def test_find_image_differences_changed_images(self):
        images_with_changed = copy.deepcopy(TEST_IMAGES)
        images_with_changed.pop(0)
        images_with_changed.append(sb.ImageInput("Ubuntu", "aaab", "abce"))
        self.assertEqual({'new': set(),
                          'changed': set(['Ubuntu']),
                          'retired': set()},
                         sb.find_image_differences(TEST_IMAGES,
                                                   images_with_changed))
        images_with_changed.pop(0)
        images_with_changed.append(sb.ImageInput("CentOS", "bbbc", "efgi"))
        self.assertEqual({'new': set(),
                          'changed': set(['Ubuntu', 'CentOS']),
                          'retired': set()},
                         sb.find_image_differences(TEST_IMAGES,
                                                   images_with_changed))

    def test_find_image_differences_retired_images(self):
        images_with_retired = copy.deepcopy(TEST_IMAGES)
        images_with_retired.pop(0)
        self.assertEqual({'new': set(),
                          'changed': set(),
                          'retired': set(['Ubuntu'])},
                         sb.find_image_differences(TEST_IMAGES,
                                                   images_with_retired))
        images_with_retired.pop(0)
        self.assertEqual({'new': set(),
                          'changed': set(),
                          'retired': set(['Ubuntu', 'CentOS'])},
                         sb.find_image_differences(TEST_IMAGES,
                                                   images_with_retired))

    def test_find_image_differences_new_images(self):
        images_with_new = copy.deepcopy(TEST_IMAGES)
        images_with_new.append(sb.ImageInput("SteamOS", "ffff", "uvwx"))
        self.assertEqual({'new': set(['SteamOS']),
                          'changed': set(),
                          'retired': set()},
                         sb.find_image_differences(TEST_IMAGES,
                                                   images_with_new))
        images_with_new.append(sb.ImageInput("WindowsServer2012", "gggg",
                                             "yzab"))
        self.assertEqual({'new': set(["SteamOS", "WindowsServer2012"]),
                          'changed': set(),
                          'retired': set()},
                         sb.find_image_differences(TEST_IMAGES,
                                                   images_with_new))

    def test_find_image_differences_all_diffs(self):
        images_with_all = copy.deepcopy(TEST_IMAGES)
        images_with_all.pop(0)
        images_with_all.pop(0)
        images_with_all.append(sb.ImageInput("Ubuntu", "aaab", "abce"))
        images_with_all.append(sb.ImageInput("SteamOS", "ffff", "uvwx"))
        self.assertEqual({'new': set(['SteamOS']),
                          'changed': set(['Ubuntu']),
                          'retired': set(['CentOS'])},
                         sb.find_image_differences(TEST_IMAGES,
                                                   images_with_all))

    def test_find_flavor_differences_no_differences(self):
        empty_flavor_diff = {'new': set(), 'retired': set()}
        self.assertEqual(empty_flavor_diff,
                         sb.find_flavor_differences([], []))
        self.assertEqual(empty_flavor_diff,
                         sb.find_flavor_differences(TEST_FLAVORS,
                                                    TEST_FLAVORS))

    def test_find_flavor_differences_new_flavors(self):
        flavors_with_new = copy.deepcopy(TEST_FLAVORS)
        flavors_with_new.append(sb.FlavorInput('GraphicalCompute',
                                               lambda node: True))
        self.assertEqual({'new': set(['GraphicalCompute']),
                          'retired': set()},
                         sb.find_flavor_differences(TEST_FLAVORS,
                                                    flavors_with_new))
        flavors_with_new.append(sb.FlavorInput("BitcoinMiner",
                                               lambda node: False))
        self.assertEqual({'new': set(["GraphicalCompute", "BitcoinMiner"]),
                          'retired': set()},
                         sb.find_flavor_differences(TEST_FLAVORS,
                                                    flavors_with_new))

    def test_find_flavor_differences_retired_flavors(self):
        flavors_with_retired = copy.deepcopy(TEST_FLAVORS)
        flavors_with_retired.pop(0)
        self.assertEqual({'new': set(),
                          'retired': set(['IO'])},
                         sb.find_flavor_differences(TEST_FLAVORS,
                                                    flavors_with_retired))
        flavors_with_retired.pop(0)
        self.assertEqual({'new': set(),
                          'retired': set(['IO', 'Compute'])},
                         sb.find_flavor_differences(TEST_FLAVORS,
                                                    flavors_with_retired))

    def test_find_flavor_differences_all_diffs(self):
        flavors_with_all_diffs = copy.deepcopy(TEST_FLAVORS)
        flavors_with_all_diffs.pop(0)
        flavors_with_all_diffs.append(sb.FlavorInput('GraphicalCompute',
                                                     lambda node: True))
        self.assertEqual({'new': set(['GraphicalCompute']),
                          'retired': set(['IO'])},
                         sb.find_flavor_differences(TEST_FLAVORS,
                                                    flavors_with_all_diffs))


class TestNodeStatistics(test_base.TestCase):

    def setUp(self):
        super(TestNodeStatistics, self).setUp()
        self.test_nodes = [
            sb.NodeInput('c-1', 'Compute', False, True, 'aaaa'),
            sb.NodeInput('c-2', 'Compute', False, True, 'aaaa'),
            sb.NodeInput('c-3', 'Compute', False, True, 'aaaa'),
            sb.NodeInput('c-4', 'Compute', True, False, 'aaaa'),
            sb.NodeInput('c-5', 'Compute', True, False, 'aaaa'),
            sb.NodeInput('c-6', 'Compute', True, False, 'aaaa'),
            sb.NodeInput('c-7', 'Compute', False, True, 'bbbb'),
            sb.NodeInput('c-8', 'Compute', False, True, 'bbbb'),
            sb.NodeInput('c-9', 'Compute', True, True, 'bbbb'),
            sb.NodeInput('c-10', 'Compute', False, True, 'cccc'),
            sb.NodeInput('c-11', 'Compute', False, False, None),
            sb.NodeInput('c-12', 'Compute', False, False, None),
            # NOTE(ClifHouck): The following uuid should not be present in
            # TEST_IMAGES. Tests reaction to unknown uuids.
            sb.NodeInput('c-13', 'Compute', False, True, 'wasd'),
        ]

    def test_build_node_statistics(self):
        stats = sb.build_node_statistics(self.test_nodes, TEST_IMAGES)

        # Make sure the stats match the node inputs above.
        self.assertEqual(13, stats['total'])
        self.assertEqual(4, stats['provisioned'])
        self.assertEqual(9, stats['not provisioned'])
        self.assertEqual(2, stats['available (not cached)'])
        self.assertEqual(7, stats['cached (includes \'caching\')'])
        self.assertEqual(3, stats['images']['Ubuntu'])
        self.assertEqual(2, stats['images']['CentOS'])
        self.assertEqual(1, stats['images']['CoreOS'])

        EXPECTED_STATS_KEYS = (
            'provisioned',
            'not provisioned',
            'available (not cached)',
            'cached (includes \'caching\')',
            'total',
            'images'
        )

        # Do some sanity checks on keys present.
        self.assertItemsEqual(EXPECTED_STATS_KEYS, stats.keys())
        # Images with non-zero counts. Includes the unrecognized UUID.
        EXPECTED_IMAGE_NAMES = ['Ubuntu', 'CentOS', 'CoreOS', 'wasd']
        self.assertItemsEqual(EXPECTED_IMAGE_NAMES, stats['images'].keys())

        @mock.patch.object(sb.LOG, 'info')
        def test_log_node_statistics(self, info_log_mock):
            stats = sb.build_node_statistics(self.test_nodes, TEST_IMAGES)
            sb.log_node_statistics(stats)
            self.assertTrue(info_log_mock.called)


class TestImageWeights(test_base.TestCase):

    def setUp(self):
        super(TestImageWeights, self).setUp()
        self._setup_weights()
        sb._load_image_weights_file.image_weights = self.WEIGHTED_IMAGES
        sb._load_image_weights_file.loaded = True

    def _setup_weights(self):
        self.NO_WEIGHTS = {}
        self.WEIGHTED_IMAGES = {
            'Ubuntu': 5,
            'CoreOS': 10,
            'Windows': 3,
            'Redhat': 2,
            'CentOS': 4,
            'Arch': 1,
            'TempleOS': 8,
            'Minix': 4
        }
        self.IMAGE_WEIGHT_SUM = sum(
            [w for i, w in six.iteritems(self.WEIGHTED_IMAGES)])
        self.EJECTION_IMAGES = [
            sb.ImageInput('Ubuntu', "aaaa", "abcd"),
            sb.ImageInput('CoreOS', "bbbb", "efgh"),
            sb.ImageInput('Windows', "cccc", "ijkl"),
            sb.ImageInput('Redhat', "dddd", "mnop"),
            sb.ImageInput('CentOS', "eeee", "qrst"),
            sb.ImageInput('Arch', "ffff", "uvwx"),
            sb.ImageInput('TempleOS', "gggg", "yzzy"),
            sb.ImageInput('Minix', "hhhh", "xwvu"),
        ]
        self.EJECTION_IMAGES_BY_NAME = {image.name: image
                                        for image in self.EJECTION_IMAGES}

    def test_load_image_weights(self):
        sb._load_image_weights_file.image_weights = {}
        sb._load_image_weights_file.loaded = False

        temp_image_weights_file = tempfile.NamedTemporaryFile()
        temp_image_weights_file.write(six.b(json.dumps(self.WEIGHTED_IMAGES)))
        temp_image_weights_file.flush()
        CONF.set_override('image_weights_filename',
                          temp_image_weights_file.name, 'strategy')

        sb._load_image_weights_file()

        self.assertEqual(sb._load_image_weights_file.image_weights,
                         self.WEIGHTED_IMAGES)
        self.assertTrue(sb._load_image_weights_file.loaded)

    @mock.patch.object(sb, '_load_image_weights_file')
    def test_get_configured_strategy_loads_image_weights(self, load_file_mock):
        CONF.set_override('percentage_to_cache', 1,
                          'simple_proportional_strategy')
        sb.get_configured_strategy()
        self.assertTrue(load_file_mock.called)

    @mock.patch.object(sb.LOG, 'exception')
    def test_exception_fails_image_weight_loading(self, exception_log_mock):
        sb._load_image_weights_file.loaded = False
        sb._load_image_weights_file.image_weights = {}
        CONF.set_override(
            'image_weights_filename',
            os.path.join('from_fox_two_phantoms_were_born',
                         'those_who_dont_exist'),
            'strategy')

        sb._load_image_weights_file()

        self.assertTrue(
            exception_log_mock.called,
            "The exception log method was not called, even though the file "
            "doesn't exist.")
        self.assertFalse(
            sb._load_image_weights_file.loaded,
            "_load_image_weights_file.loaded is True, even though it "
            "did not load a file.")
        self.assertEqual(
            {},
            sb._load_image_weights_file.image_weights,
            "_load_image_weights_file.image_weights is not equal to {} "
            "even though no file was loaded.")

    def test_reload_weight_file_when_true(self):
        temp_image_weights_file = tempfile.NamedTemporaryFile()
        test_weights = {'the_final_countdown': 5,
                        'the_man_who_sold_the_world': 10}
        temp_image_weights_file.write(six.b(json.dumps(test_weights)))
        temp_image_weights_file.flush()
        CONF.set_override('image_weights_filename',
                          temp_image_weights_file.name, 'strategy')

        sb._load_image_weights_file(reload_file=True)

        self.assertEqual(sb._load_image_weights_file.image_weights,
                         test_weights)
        self.assertTrue(sb._load_image_weights_file.loaded)

    def test_reload_weight_file_when_false(self):
        temp_image_weights_file = tempfile.NamedTemporaryFile()
        test_weights = {'the_final_countdown': 5,
                        'the_man_who_sold_the_world': 10}
        temp_image_weights_file.write(six.b(json.dumps(test_weights)))
        temp_image_weights_file.flush()
        CONF.set_override('image_weights_filename',
                          temp_image_weights_file.name, 'strategy')

        sb._load_image_weights_file(reload_file=False)

        self.assertEqual(sb._load_image_weights_file.image_weights,
                         self.WEIGHTED_IMAGES)
        self.assertTrue(sb._load_image_weights_file.loaded)

    def test_get_image_weights(self):
        weights_by_name = sb.get_image_weights(
            ['Ubuntu', 'CoreOS', 'SomeWeirdImage'])
        self.assertItemsEqual(weights_by_name.keys(),
                              ['Ubuntu', 'CoreOS', 'SomeWeirdImage'])

        self.assertEqual(5, weights_by_name['Ubuntu'])
        self.assertEqual(10, weights_by_name['CoreOS'])
        self.assertEqual(CONF.strategy.default_image_weight,
                         weights_by_name['SomeWeirdImage'])

        random_image_names = ['bunch', 'of', 'random', 'image', 'names']
        weights_by_name = sb.get_image_weights(random_image_names)
        self.assertItemsEqual(weights_by_name.keys(), random_image_names)
        for key, value in six.iteritems(weights_by_name):
            self.assertEqual(CONF.strategy.default_image_weight, value)

    def test_determine_image_distribution(self):
        TEST_NODE_SET = [
            sb.NodeInput('c-1', 'compute', False, True, 'aaaa'),
            sb.NodeInput('c-2', 'compute', False, False, 'bbbb'),
            sb.NodeInput('c-3', 'compute', True, False, 'cccc'),
            sb.NodeInput('c-4', 'compute', False, True, 'aaaa'),
            sb.NodeInput('c-5', 'compute', False, True, 'bbbb'),
            sb.NodeInput('c-6', 'compute', False, True, 'dddd')
        ]
        distribution_by_uuid = sb._determine_image_distribution(TEST_NODE_SET)
        self.assertEqual(2, distribution_by_uuid['aaaa'])
        self.assertEqual(1, distribution_by_uuid['bbbb'])
        self.assertEqual(1, distribution_by_uuid['dddd'])
        self.assertEqual(0, distribution_by_uuid['cccc'])

    def test_choose_weighted_images_forced_distribution(self):
        test_scenarios = {
            '10-all nodes available': {
                'num_images': 10,
                'images': TEST_IMAGES,
                'nodes': [sb.NodeInput('c-%d' % (n), 'compute', False, False,
                                       'aaaa') for n in range(0, 10)]
            },
            '100-all nodes available': {
                'num_images': 50,
                'images': TEST_IMAGES,
                'nodes': [sb.NodeInput('c-%d' % (n), 'compute', False, False,
                                       'aaaa') for n in range(0, 100)]
            },
            '1000-all nodes available': {
                'num_images': 1000,
                'images': TEST_IMAGES,
                'nodes': [sb.NodeInput('c-%d' % (n), 'compute', False, False,
                                       'aaaa') for n in range(0, 1000)]
            },
            'all nodes available - num of nodes machine image weight sum': {
                'num_images': self.IMAGE_WEIGHT_SUM,
                'images': TEST_IMAGES,
                'nodes': [sb.NodeInput('c-%d' % (n), 'compute', False, False,
                          'aaaa') for n in range(0, self.IMAGE_WEIGHT_SUM)]
            },
        }

        # Provides a list which coupled with random selection should
        # closely match the image weights. Therefore already cached nodes
        # in these scenarios already closely match the distribution.
        weighted_image_uuids = []
        for image in TEST_IMAGES:
            weighted_image_uuids.extend(
                [image.uuid
                 for n in range(0, self.WEIGHTED_IMAGES[image.name])])

        images_by_uuids = {image.uuid: image for image in TEST_IMAGES}

        # Generate some more varied scenarios.
        for num_nodes in [1, 2, 3, 5, 10, 20, 50, 100, 1000, 10000]:
            new_scenario = {
                'images': TEST_IMAGES,
                'num_images': int(math.floor(num_nodes * 0.25)),
                'nodes': []
            }
            for n in range(0, num_nodes):
                cached = n % 4 == 0
                provisioned = n % 7 == 0
                cached_image_uuid = random.choice(weighted_image_uuids)
                generated_node = sb.NodeInput("c-%d" % (n),
                                              'compute',
                                              provisioned,
                                              cached,
                                              cached_image_uuid)
                new_scenario['nodes'].append(generated_node)
            test_scenarios['%d-random scenario' % (num_nodes)] = new_scenario

        # Now test each scenario.
        for name, values in six.iteritems(test_scenarios):
            print("Testing against '%s' scenario." % (name))
            picked_images = sb.choose_weighted_images_forced_distribution(
                **values)

            picked_distribution = collections.defaultdict(lambda: 0)
            for image in picked_images:
                picked_distribution[image.name] += 1

            self.assertEqual(values['num_images'], len(picked_images),
                             "Didn't get the expected number of selected "
                             "images from "
                             "choose_weighted_images_forced_distribution")

            num_already_cached = len([node for node in values['nodes']
                                      if node.cached and not node.provisioned])
            scale = (num_already_cached + values['num_images']) / sum(
                [self.WEIGHTED_IMAGES[image.name] for image in TEST_IMAGES])

            already_cached = collections.defaultdict(lambda: 0)
            for node in values['nodes']:
                if node.cached and not node.provisioned:
                    image = images_by_uuids[node.cached_image_uuid]
                    already_cached[image.name] += 1

            targeted_distribution = {
                image.name: (picked_distribution[image.name] +
                             already_cached[image.name])
                for image in TEST_IMAGES
            }

            print(''.join(["Picked distribution: %s\n" % (
                           str(picked_distribution)),
                           "Already cached distribution: %s\n" % (
                           str(already_cached)),
                           "Targeted distribution: %s\n" % (
                           str(targeted_distribution)),
                           "Image weights: %s\n" % str(self.WEIGHTED_IMAGES),
                           "scale factor: %f" % scale]))

            for image in values['images']:
                print("Inspecting image '%s'." % (image.name))
                image_weight = self.WEIGHTED_IMAGES[image.name]
                num_image_already_cached = len([
                    node for node in values['nodes'] if node.cached and
                    not node.provisioned and
                    node.cached_image_uuid == image.uuid])
                expected_num_of_selected_images = (
                    int(math.floor(scale * image_weight)) -
                    num_image_already_cached)
                # Sometimes an underweighted image will be cached a great deal
                # more than should be given the current weights. Clamp this
                # the expectation to zero.
                if expected_num_of_selected_images < 0:
                    expected_num_of_selected_images = 0
                num_picked = len(
                    [pi for pi in picked_images if pi.name == image.name])
                failure_msg = (
                    "The number of selected images for image "
                    "'%(image_name)s' did not match expectations. "
                    "Expected %(expected)d and got %(actual)d. " %
                    {'image_name': image.name,
                     'expected': expected_num_of_selected_images,
                     'actual': num_picked})
                self.assertAlmostEqual(num_picked,
                                       expected_num_of_selected_images,
                                       delta=1,
                                       msg=failure_msg)

    def test_image_weight_guided_node_ejection(self):
        test_envs = {
            'Already ideal distribution': {},
            'Ubuntu+10': {'Ubuntu': 10},
            'CentOS+5': {'CentOS': 5},
            'Ubuntu and CoreOS': {'Ubuntu': 10, 'CoreOS': 20},
            'TempleOS': {'TempleOS': 50},
            'A lot of minix!': {'Minix': 100},
            'Many offsets': {'Ubuntu': 4, 'Minix': 3, 'Redhat': 2,
                             'CoreOS': 1},
        }

        for env_name, image_offsets in six.iteritems(test_envs):
            print("Testing '%(name)s' on image_weight_guided_ejection." % {
                  'name': env_name})
            nodes = []

            image_frequencies = copy.deepcopy(self.WEIGHTED_IMAGES)
            for image_name, offset in six.iteritems(image_offsets):
                image_frequencies[image_name] += offset

            # Construct a set of nodes with the desired frequency
            for image_name, frequency in six.iteritems(image_frequencies):
                image = self.EJECTION_IMAGES_BY_NAME[image_name]
                for n in range(0, frequency):
                    nodes.append(
                        sb.NodeInput('c-%d' % len(nodes), 'compute',
                                     False, True, image.uuid))

            image_list = sb.image_weight_guided_ejection(self.EJECTION_IMAGES,
                                                         nodes)

            eject_frequencies = collections.defaultdict(lambda: 0)
            for image in image_list:
                eject_frequencies[image.name] += 1

            eject_frequency_list = (
                [(k, v) for k, v in six.iteritems(eject_frequencies)])

            eject_frequency_list.sort(key=lambda pair: pair[1])

            sorted_ejection_list = (
                [image_name for image_name, frequency in eject_frequency_list])

            if len(image_offsets) == 0:
                self.assertEqual(0, len(image_offsets))
                return

            named_offsets = [(n, o) for n, o in six.iteritems(image_offsets)]
            sorted_offsets = sorted(named_offsets, key=lambda pair: pair[1])

            expected_sorted_ejection_list = (
                [image_name for image_name, offset in sorted_offsets])

            # The number of kinds of images ejected shouldn't exceed our
            # expected number of kinds.
            self.assertTrue(
                (len(sorted_ejection_list) <=
                    len(expected_sorted_ejection_list)))

            # It's OK if the number of kinds returned is less than expected,
            # as long as the relative order is maintained.
            if len(expected_sorted_ejection_list) > len(sorted_ejection_list):
                length_diff = (len(expected_sorted_ejection_list) -
                               len(sorted_ejection_list))
                expected_sorted_ejection_list = (
                    expected_sorted_ejection_list[length_diff:])

            # We make sure that the relative ejection rate of images matches
            # our general expectation.
            self.assertEqual(expected_sorted_ejection_list,
                             sorted_ejection_list)

    def test_images_with_zero_weight_not_cached(self):
        image_weights = {
            'Ubuntu': 5,
            'CoreOS': 10,
            'Windows': 0,
        }

        sb._load_image_weights_file.image_weights = image_weights

        CONF.set_override('default_image_weight', 0, 'strategy')

        test_scenario = {
            'num_images': 30,
            'images': TEST_IMAGES,
            'nodes': (
                [sb.NodeInput('c-%d' % n, 'compute', False, False, 'aaaa') for
                    n in range(0, 30)])
        }

        picked_images = (
            sb.choose_weighted_images_forced_distribution(**test_scenario))

        # Make sure no images were picked with a zero weight.
        expected_names = [name for name, weight in six.iteritems(image_weights)
                          if weight > 0]
        for image in picked_images:
            self.assertIn(image.name, expected_names,
                          "Found an unexpected image cached. Image had a "
                          "zero weight. Image name %s" % (image.name))
