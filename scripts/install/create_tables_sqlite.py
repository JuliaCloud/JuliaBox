#! /usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "engine", "src"))

import sqlite3

from juliabox.db import JBoxUserV2, JBoxDynConfig, JBoxSessionProps, JBPluginDB, JBoxAPISpec

# import any plugins that contribute tables
import juliabox.plugins.course_homework


def table_exists(table_name):
    try:
        c.execute("select * from %s where 1=0" % (table_name,))
        c.fetchall()
        return c.description is not None
    except:
        return False


def table_create(table_name, columns, keys=None):
    allcolumns = columns if keys is None else keys + columns
    sql = 'create table %s (%s' % (table_name, ', '.join(allcolumns))
    if keys is not None:
        sql += (', primary key (%s)' % (', '.join(keys),))
    sql += ')'
    c.execute(sql)
    conn.commit()

print("connecting to %s" % (sys.argv[1],))
conn = sqlite3.connect(sys.argv[1])
c = conn.cursor()

tables = [JBoxUserV2, JBoxDynConfig, JBoxSessionProps, JBoxAPISpec]
for plugin in JBPluginDB.jbox_get_plugins(JBPluginDB.JBP_TABLE_RDBMS):
    tables.append(plugin)

for cls in tables:
    print("Creating %s..." % (cls.NAME,))
    if table_exists(cls.NAME):
        print("\texists already!")
    else:
        table_create(cls.NAME, cls.ATTRIBUTES, cls.KEYS)
        print("\tcreated.")
