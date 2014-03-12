#    Copyright (c) 2014 Rackspace Hosting
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

from trove.tests.unittests.datastore.base import TestDatastoreBase
from trove.datastore.models import Capability
from trove.common.exception import CapabilityNotFound


class TestCapabilities(TestDatastoreBase):
    def setUp(self):
        super(TestCapabilities, self).setUp()

        self.capability_name = "root_on_create-" + self.test_id
        self.capability_desc = "Enables root on create"

        Capability.create(
            name=self.capability_name,
            description=self.capability_desc
        )

    def tearDown(self):
        super(TestCapabilities, self).tearDown()
        Capability.load(self.capability_name).delete()

    def test_capability(self):
        self.assertEqual(Capability.load(self.capability_name).name,
                         self.capability_name)

    def test_capability_create_disabled(self):
        capability = Capability.create("disabled" + self.test_id,
                                       "disabled test capability", False)

        self.assertFalse(capability.enabled)
        capability.delete()

    def test_capability_enabled(self):
        self.assertTrue(Capability.load(self.capability_name).enabled)

    def test_capability_disabled(self):
        capability = Capability.load(self.capability_name)
        capability.disable()
        self.assertFalse(capability.enabled)

        self.assertFalse(Capability.load(self.capability_name).enabled)

    def test_load_nonexistant_capability(self):
        self.assertRaises(CapabilityNotFound, Capability.load, "non-existant")
