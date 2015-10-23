# -*- coding: utf-8 -*-

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

"""
test_onmetal_scout
----------------------------------

Tests for `onmetal_scout` module.
"""
import copy
import uuid

import mock
from oslo_config import cfg

import arsenal.director.onmetal_scout as onmetal
from arsenal.external import client_wrapper
import arsenal.strategy.base as strat_base
from arsenal.tests.unit import base

CONF = cfg.CONF

TEST_IRONIC_NODE_DATA = {
    "target_power_state": None,
    "links": [
        {
            "href": "http://localhost",
            "rel": "self"
        },
        {
            "href": "http://localhost/node_uuid",
            "rel": "bookmark"
        }
    ],
    "extra": {
        "flavor": "onmetal-compute1",
    },
    "last_error": None,
    "updated_at": "2015-10-16T17:33:09+00:00",
    "maintenance_reason": None,
    "provision_state": "available",
    "clean_step": {},
    "uuid": str(uuid.uuid4()),
    "console_enabled": False,
    "target_provision_state": None,
    "provision_updated_at": "2015-10-16T08:05:10+00:00",
    "power_state": "power on",
    "inspection_started_at": None,
    "inspection_finished_at": None,
    "maintenance": False,
    "driver": "agent_ipmitool",
    "reservation": None,
    "properties": {
        "memory_mb": 32768,
        "cpu_arch": "amd64",
        "local_gb": 32,
        "cpus": 20
    },
    "instance_uuid": None,
    "name": None,
    "driver_info": {
        "cache_image_id": str(uuid.uuid4()),
        "hardware_manager_version": None,
        "ipmi_username": "clif",
        "ipmi_address": "127.0.0.1",
        "decommission_target_state": None,
        "ipmi_password": "******",
        "agent_url": "http://127.0.0.1:9999",
        "cache_status": "cached",
        "agent_last_heartbeat": 1430428362
    },
    "created_at": "2014-05-29T23:41:17+00:00",
    "ports": [
        {
            "href": "http://localhost/",
            "rel": "self"
        },
        {
            "href": "http://localhost/",
            "rel": "bookmark"
        }
    ],
    "driver_internal_info": {
        "clean_steps": None,
        "hardware_manager_version": {
            "generic_hardware_manager": "5",
            "AnotherHardwareManager": "5",
            "SSDHardwareManager": "5",
            "NICHardwareManager": "6"
        },
        "is_whole_disk_image": True,
        "agent_erase_devices_iterations": 1,
        "agent_url": "http://127.0.0.1:9999",
        "cleaning_reboot": True,
        "agent_last_heartbeat": 1445016789
    },
    "instance_info": {}
}


class MockIronicNode(object):
    def __init__(self, ironic_data):
        for key in ironic_data.keys():
            setattr(self, key, copy.deepcopy(ironic_data[key]))


TEST_GLANCE_IMAGE_DATA = [
    {
        'flavor_classes': 'onmetal',
        'vm_mode': 'metal',
        'visibility': 'public',
        'name': 'ubuntu-14.04',
        'id': 'aaaa',
        'checksum': 'ubuntu-checksum',
        'file': 'ubuntu_14_04_image.pxe'
    },
    {
        'flavor_classes': 'onmetal',
        'vm_mode': 'metal',
        'visibility': 'public',
        'name': 'ubuntu-14.10',
        'id': 'bbbb',
        'checksum': 'ubuntu-checksum',
        'file': 'ubuntu_14_10_image.pxe'
    },
    {
        'flavor_classes': 'onmetal',
        'vm_mode': 'metal',
        'visibility': 'public',
        'name': 'coreos',
        'id': 'cccc',
        'checksum': 'coreos-checksum',
        'file': 'coreos_image.pxe'
    },
    {
        'flavor_classes': '!onmetal',
        'vm_mode': 'metal',
        'visibility': 'public',
        'name': 'ubuntu-14.04_not_onmetal',
        'id': 'dddd',
        'checksum': 'ubuntu-not-onmetal-checksum',
        'file': 'ubuntu_14_04_not_onmetal_image.pxe'
    },
    {
        'flavor_classes': 'onmetal',
        'vm_mode': 'not_onmetal',
        'visibility': 'public',
        'name': 'ubuntu-14.04_vm_mode_not_onmetal',
        'id': 'eeee',
        'checksum': 'ubuntu-vm_mode_not_onmetal_checksum',
        'file': 'ubuntu_14_04_vm_mode_not_onmetal_image.pxe'
    },
    {
        'flavor_classes': 'onmetal',
        'vm_mode': 'metal',
        'visibility': 'private',
        'name': 'coreos_private',
        'id': 'cccc',
        'checksum': 'coreos-private-checksum',
        'file': 'coreos_private.pxe'
    },
]

GLANCE_IMAGE_DATA_BY_NAME = {
    image['name']: image for image in TEST_GLANCE_IMAGE_DATA
}


class FakeFlavor(object):
    def __init__(self, flavor_id, ram):
        self.id = flavor_id
        self.ram = ram


TEST_NOVA_FLAVOR_DATA = [
    FakeFlavor('onmetal-compute1', 32768),
    FakeFlavor('onmetal-io1', 131072),
    FakeFlavor('onmetal-memory1', 524288),
    FakeFlavor('onmetal-gpu1', 65536),
    FakeFlavor('some_other_flavor', 1024),
    FakeFlavor('flavor_that_doesnt_start_with_onmetal', 2048),
    FakeFlavor('onmetal_doesnt_match', 4096),
]


class TestOnMetalScout(base.TestCase):

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, 'call')
    def setUp(self, wrapper_call_mock):
        super(TestOnMetalScout, self).setUp()
        CONF.set_override('api_endpoint', 'http://glance_endpoint', 'glance')
        wrapper_call_mock.return_value = TEST_GLANCE_IMAGE_DATA
        self.scout = onmetal.OnMetalScout()
        self.scout.retrieve_image_data()

    def test_is_node_provisioned(self):
        ironic_node = mock.NonCallableMock()

        # Maintenanced nodes count as provisioned.
        ironic_node.provision_state = None
        ironic_node.maintenance = True
        self.assertTrue(onmetal.is_node_provisioned(ironic_node))

        # Not maintenanced, but has a provision state that is not 'available'.
        ironic_node.provision_state = "cleaning"
        ironic_node.maintenance = False
        self.assertTrue(onmetal.is_node_provisioned(ironic_node))

        # Not maintenanced, and has a provision state that is 'available'.
        ironic_node.provision_state = "available"
        self.assertFalse(onmetal.is_node_provisioned(ironic_node))

        # No provision state nor in maintenance, so not provisioned.
        ironic_node.provision_state = None
        self.assertFalse(onmetal.is_node_provisioned(ironic_node))

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, 'call')
    def test_issue_cache_node_good_image(self, wrapper_call_mock):
        cache_node_action = strat_base.CacheNode('node_uuid',
                                                 'aaaa',
                                                 'ubuntu-checksum')
        expected_args = {
            'image_info': {
                'id': 'aaaa',
                'urls': [CONF.glance.api_endpoint + 'ubuntu_14_04_image.pxe'],
                'checksum': 'ubuntu-checksum'
            }
        }
        self.scout.issue_cache_node(cache_node_action)
        wrapper_call_mock.assert_called_once_with('node.vendor_passthru',
                                                  node_id='node_uuid',
                                                  method='cache_image',
                                                  http_method='POST',
                                                  args=expected_args)

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, 'call')
    def test_issue_cache_node_bad_image(self, wrapper_call_mock):
        cache_node_action = strat_base.CacheNode('node_uuid',
                                                 'zzzz',
                                                 'ubuntu-checksum')
        self.scout.issue_cache_node(cache_node_action)
        self.assertFalse(wrapper_call_mock.called,
                         "The client should not have been called because "
                         "a bad image uuid was passed!")

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, 'call')
    def test_retrieve_flavor_data_only_returns_onmetal(self,
                                                       wrapper_call_mock):
        wrapper_call_mock.return_value = TEST_NOVA_FLAVOR_DATA
        result = self.scout.retrieve_flavor_data()
        expected_flavors = ('onmetal-compute1', 'onmetal-io1', 'onmetal-gpu1',
                            'onmetal-memory1')

        # NOTE(ClifHouck): This also implicitly tests retrieve_flavor_data's
        # behavior to add unknown flavors to onmetal_scout.KNOWN_FLAVORS.
        expected_result = [
            strat_base.FlavorInput(f, onmetal.KNOWN_FLAVORS.get(f))
            for f in expected_flavors
        ]
        self.assertItemsEqual([e.name for e in expected_result],
                              [r.name for r in result],
                              "retrieve_flavor_data did not properly filter "
                              "for onmetal flavors!")

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, 'call')
    def test_retrieve_image_data_only_returns_onmetal(self,
                                                      wrapper_call_mock):
        wrapper_call_mock.return_value = TEST_GLANCE_IMAGE_DATA
        result = self.scout.retrieve_image_data()
        expected_images = ('ubuntu-14.04', 'ubuntu-14.10', 'coreos')
        expected_result = [
            strat_base.ImageInput(i,
                                  GLANCE_IMAGE_DATA_BY_NAME[i]['id'],
                                  GLANCE_IMAGE_DATA_BY_NAME[i]['checksum'])
            for i in expected_images
        ]
        self.assertItemsEqual([e.name for e in expected_result],
                              [r.name for r in result],
                              "retrieve_image_data did not properly filter "
                              "for onmetal images!")

    @mock.patch.object(client_wrapper.OpenstackClientWrapper, 'call')
    def test_issue_eject_node_calls_manage_and_provide(self,
                                                       wrapper_call_mock):
        eject_node_action = strat_base.EjectNode('node_uuid')
        self.scout.issue_eject_node(eject_node_action)
        calls = [
            mock.call('node.set_provision_state', node_uuid='node_uuid',
                      state='manage'),
            mock.call('node.set_provision_state', node_uuid='node_uuid',
                      state='provide')
        ]
        wrapper_call_mock.assert_has_calls(calls)

    def test_convert_ironic_node(self):
        test_node = MockIronicNode(TEST_IRONIC_NODE_DATA)
        node_input = onmetal.convert_ironic_node(test_node)
        expected_node = strat_base.NodeInput(
            TEST_IRONIC_NODE_DATA['uuid'],
            TEST_IRONIC_NODE_DATA['extra']['flavor'],
            False,
            True,
            TEST_IRONIC_NODE_DATA['driver_info']['cache_image_id'])
        for attr in ('node_uuid', 'flavor', 'provisioned',
                     'cached', 'cached_image_uuid'):
            expected = getattr(expected_node, attr)
            got = getattr(node_input, attr)
            self.assertEqual(expected, got,
                             "Attribute on node returned by "
                             "convert_ironic_node did not match expectations. "
                             "Expected '%(expected)s', got '%(got)s'." % (
                                {'expected': expected, 'got': got}))

    def test_resolve_flavor_extra_is_not_set(self):
        test_node = MockIronicNode(TEST_IRONIC_NODE_DATA)
        test_node.extra = None
        # Should still be able to resolve the flavor.
        flavor = onmetal.resolve_flavor(test_node)
        self.assertEqual("onmetal-compute1", flavor,
                         "Flavor returned by resolve_flavor does not match "
                         "expectations. Got '%(got)s', "
                         "expected '%(expected)s'." % (
                            {'got': flavor, 'expected': "onmetal-compute1"}))

    def test_resolve_flavor_extra_is_set(self):
        test_node = MockIronicNode(TEST_IRONIC_NODE_DATA)
        expected_flavor = "onmetal-some_exotic_flavor"
        test_node.extra['flavor'] = expected_flavor
        flavor = onmetal.resolve_flavor(test_node)
        self.assertEqual(expected_flavor, flavor,
                         "Flavor returned by resolve_flavor does not match "
                         "expectations. Got '%(got)s', "
                         "expected '%(expected)s'." % (
                            {'got': flavor, 'expected': expected_flavor}))

    def test_resolve_flavor_does_not_resolve(self):
        test_node = MockIronicNode(TEST_IRONIC_NODE_DATA)
        test_node.extra = None
        test_node.properties['memory_mb'] = 1337
        flavor = onmetal.resolve_flavor(test_node)
        self.assertEqual(None, flavor,
                         "Flavor returned by resolve_flavor does not match "
                         "expectations. Got '%(got)s', "
                         "expected None." % ({'got': flavor}))
