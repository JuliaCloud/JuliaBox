#! /usr/bin/env python

from boto.dynamodb2.table import Table

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "engine", "src"))

from juliabox.db import JBoxUserV2, JBoxDynConfig, JBoxSessionProps, JBPluginDB, JBoxAPISpec

# import any plugins that contribute tables
import juliabox.plugins.course_homework
import juliabox.plugins.usage_accounting
import juliabox.plugins.vol_ebs


def table_exists(name):
    t = Table(name)
    try:
        t.describe()
        return True
    except:
        return False

tables = [JBoxUserV2, JBoxDynConfig, JBoxSessionProps, JBoxAPISpec]
for plugin in JBPluginDB.jbox_get_plugins(JBPluginDB.JBP_TABLE_DYNAMODB):
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
