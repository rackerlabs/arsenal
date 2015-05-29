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
import copy

from oslo.config import cfg

from arsenal.strategy import base as sb
from arsenal.tests import base as test_base

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
