# -*- coding: utf-8 -*-

# Copyright 2016 Rackspace
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

"""
test_onmetal_scout
----------------------------------

Tests for `onmetal_scout` module.
"""

import mock

import arsenal.director.onmetal_scout as onmetal
from arsenal.tests.unit import base


class TestOnMetalScouts(base.TestCase):
    def setUp(self):
        super(TestOnMetalScouts, self).setUp()
        self.onmetal_v1_scout = onmetal.OnMetalV1Scout()
        self.onmetal_v2_scout = onmetal.OnMetalV2Scout()

    def test_is_onmetal_flavor_v2(self):
        fake_flavor = mock.Mock()
        true_cases = ('onmetal-io2', 'onmetal-small2',
                      'onmetal-general2-small',
                      'onmetal-general2-medium',
                      'onmetal-general2-large')
        false_cases = ('onmetal2', 'asdflklj;', '', '2')

        for case in true_cases:
            fake_flavor.id = case
            self.assertTrue(onmetal.is_onmetal_v2_flavor(fake_flavor),
                            "%s should be a v2 flavor!" % case)

        for case in false_cases:
            fake_flavor.id = case
            self.assertFalse(onmetal.is_onmetal_v2_flavor(fake_flavor),
                             "%s should NOT be a v2 flavor!" % case)

    def test_is_onmetal_image(self):
        onmetal_images = (
            {
                'flavor_classes': ['onmetal'],
                'vm_mode': 'metal',
                'visibility': 'public'
            },
            {
                'flavor_classes': ['onmetal', 'asdf'],
                'vm_mode': 'metal',
                'visibility': 'public'
            }
        )
        not_onmetal_images = (
            {
                'flavor_classes': ['virt', '!onmetal'],
                'vm_mode': 'wut',
                'visibility': 'private'
            },
            {
                'flavor_classes': ['onmetal'],
                'vm_mode': 'metal',
                'visibility': 'private'
            },
            {
                'flavor_classes': ['onmetal'],
                'vm_mode': 'virt',
                'visibility': 'public'
            },
        )

        for image in onmetal_images:
            self.assertTrue(onmetal.is_onmetal_image(image, 'onmetal'))

        for image in not_onmetal_images:
            self.assertFalse(onmetal.is_onmetal_image(image, 'onmetal'))

    def test_is_v2_flavor(self):
        expected_memory_mb = 1024
        expected_local_gb = 128
        expected_cpus = 32

        our_flavor = {
            'properties': {
                'memory_mb': expected_memory_mb,
                'local_gb': expected_local_gb,
                'cpus': expected_cpus
            }
        }
        not_our_flavors = (
            {
                'properties': {
                    'memory_mb': 1025,
                    'local_gb': expected_local_gb,
                    'cpus': expected_cpus
                }
            },
            {
                'properties': {
                    'memory_mb': expected_memory_mb,
                    'local_gb': 2,
                    'cpus': expected_cpus
                }
            },
            {
                'properties': {
                    'memory_mb': expected_memory_mb,
                    'local_gb': expected_local_gb,
                    'cpus': 64
                }
            }
        )
        self.assertTrue(
            onmetal.is_v2_flavor_generic(our_flavor,
                                         expected_memory_mb,
                                         expected_local_gb,
                                         expected_cpus))

        for flavor_node in not_our_flavors:
            self.assertFalse(
                onmetal.is_v2_flavor_generic(flavor_node,
                                             expected_memory_mb,
                                             expected_local_gb,
                                             expected_cpus))
