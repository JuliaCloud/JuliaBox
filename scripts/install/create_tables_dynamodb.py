#! /usr/bin/env python

from boto.dynamodb2.table import Table

from juliabox.db import JBoxUserV2, JBoxInvite, JBoxDiskState, JBoxAccountingV2, JBoxDynConfig, \
    JBoxSessionProps, JBoxDBPlugin

# import any plugins that contribute tables
import juliabox.plugins.course_homework

def table_exists(name):
    t = Table(name)
    try:
        t.describe()
        return True
    except:
        return False

tables = [JBoxUserV2, JBoxInvite, JBoxDiskState, JBoxAccountingV2, JBoxDynConfig, JBoxSessionProps]
for plugin in JBoxDBPlugin.plugins:
    tables.append(plugin)

for cls in tables:
    print("Creating %s..." % (cls.NAME,))
    if table_exists(cls.NAME):
        print("\texists already!")
    else:
        Table.create(cls.NAME, schema=cls.SCHEMA, indexes=cls.INDEXES, throughput={
            'read': 1,
            'write': 1
        })
        print("\tcreated.")
