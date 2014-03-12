# Copyright 2014 Rackspace
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

from trove.datastore import models as datastore_models
from trove.datastore.models import Datastore
from trove.datastore.models import Capability
from trove.datastore.models import DatastoreVersion
from trove.tests.unittests.datastore.base import TestDatastoreBase
from trove.common import exception


class TestDatastore(TestDatastoreBase):
    def setUp(self):
        super(TestDatastore, self).setUp()
        self.ds_name = "my-test-datastore" + self.test_id
        self.ds_version = "my-test-version" + self.test_id

        datastore_models.update_datastore(self.ds_name, False)
        self.datastore = Datastore.load(self.ds_name)

        datastore_models.update_datastore_version(
            self.ds_name, self.ds_version, "mysql", "", "", True)

        self.datastore_version = DatastoreVersion.load(self.datastore,
                                                       self.ds_version)

    def tearDown(self):
        super(TestDatastore, self).tearDown()
        Datastore.load(self.ds_name).delete()

    def test_load_datastore_version(self):
        datastore_version = DatastoreVersion.load(self.datastore,
                                                  self.ds_version)
        self.assertEqual(datastore_version.name, self.ds_version)

    def test_datastore_version_capabilities_empty(self):
        self.assertEqual(len(self.datastore_version.capabilities), 0)

    def test_datastore_capabilities_disabled(self):
        cap1 = Capability.create("ds-test1-" + self.test_id, "Testing", False)

        self.assertRaises(
            exception.CapabilityDisabled,
            self.datastore_version.capabilities.add,
            cap1)

        cap1.delete()

    def test_datastore_verison_capabilities_not_empty(self):

        cap1 = Capability.create("ds-test1-" + self.test_id, "Testing")
        cap2 = Capability.create("ds-test2-" + self.test_id, "Testing")
        cap3 = Capability.create("ds-test3-" + self.test_id, "Testing")

        self.datastore_version.capabilities.add(cap1)
        self.assertEqual(len(self.datastore_version.capabilities), 1)

        # Test a fresh reloading of the datastore
        self.datastore_version = DatastoreVersion.load(self.datastore,
                                                       self.ds_version)
        self.assertEqual(len(self.datastore_version.capabilities), 1)

        self.datastore_version.capabilities.add(cap2)
        self.assertEqual(len(self.datastore_version.capabilities), 2)

        self.assertIn(cap1.name, self.datastore_version.capabilities)
        self.assertNotIn("non-existant", self.datastore_version.capabilities)
        self.assertNotIn(cap3.name, self.datastore_version.capabilities)

        cap1.delete()
        cap2.delete()
        cap3.delete()
