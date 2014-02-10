# Copyright 2012 OpenStack Foundation
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

from sqlalchemy import ForeignKey
from sqlalchemy.schema import Column
from sqlalchemy.schema import MetaData
from sqlalchemy.schema import UniqueConstraint

from trove.db.sqlalchemy.migrate_repo.schema import create_tables
from trove.db.sqlalchemy.migrate_repo.schema import drop_tables
from trove.db.sqlalchemy.migrate_repo.schema import String
from trove.db.sqlalchemy.migrate_repo.schema import Table


meta = MetaData()


# I couldn't get migrations to run without adding the datastores table here
datastores = Table(
    'datastores',
    meta,
    Column('id', String(36), primary_key=True, nullable=False),
    Column('name', String(255), unique=True),
    Column('manager', String(255), nullable=False),
    Column('default_version_id', String(36)),
)

capabilities = Table(
    'capabilities',
    meta,
    Column('id', String(36), primary_key=True, nullable=False),
    Column('name', String(255), unique=True),
    Column('description', String(255), nullable=False)
)

datastore_capabilities = Table(
    'datastore_capabilities',
    meta,
    Column('datastore_id', String(36), ForeignKey('datastores.id')),
    Column('capability_id', String(36), ForeignKey('capabilities.id')),
    UniqueConstraint('datastore_id', 'capability_id', name='ds_capabilities')
)



def upgrade(migrate_engine):
    meta.bind = migrate_engine
    create_tables([capabilities, datastore_capabilities])


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    drop_tables([capabilities, datastore_capabilities])
