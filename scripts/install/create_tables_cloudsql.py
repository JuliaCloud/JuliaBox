#! /usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "engine", "src"))

import MySQLdb

from juliabox.db import JBoxUserV2, JBoxDynConfig, JBoxSessionProps, JBPluginDB, JBoxAPISpec
from juliabox.jbox_util import JBoxCfg

# import any plugins that contribute tables
import juliabox.plugins.course_homework

def table_exists(table_name):
    try:
        c.execute("select * from %s where 1=0" % (table_name,))
        c.fetchall()
        return c.description is not None
    except:
        return False


def table_create(table_name, columns, types, keys=None, keys_types=None):
    stmt = []
    if keys is not None:
        for k, t in zip(keys, keys_types):
            stmt.append(k + ' ' + t)
    for col, t in zip(columns, types):
        stmt.append(col + ' ' + t)
    sql = 'create table %s (%s' % (table_name, ', '.join(stmt))
    if keys is not None:
        sql += (', primary key (%s)' % (', '.join(keys),))
    sql += ')'
    c.execute(sql)
    conn.commit()

def indexes_create(table_name, indexes):
    if indexes == None:
        return
    for idx in indexes:
        name = idx['name']
        cols = ', '.join(idx['cols'])
        sql = "CREATE INDEX `%s` ON %s(%s)" % (name, table_name, cols)
        c.execute(sql)
        conn.commit()

def get_connection():
    # Copy from /jboxengine/conf/jbox.user
    user = 'user'
    passwd = 'passwd'
    unix_socket = '/cloudsql/project:region:sqlinstance'
    db = 'JuliaBox'
    return MySQLdb.connect(user=user, passwd=passwd, db=db, unix_socket=unix_socket)

conn = get_connection()
c = conn.cursor()

tables = [JBoxUserV2, JBoxDynConfig, JBoxSessionProps, JBoxAPISpec]
for plugin in JBPluginDB.jbox_get_plugins(JBPluginDB.JBP_TABLE_DYNAMODB):
    tables.append(plugin)

for cls in tables:
    print("Creating %s..." % (cls.NAME,))
    if table_exists(cls.NAME):
        print("\texists already!")
    else:
        table_create(cls.NAME, cls.ATTRIBUTES, cls.TYPES, cls.KEYS, cls.KEYS_TYPES)
        indexes_create(cls.NAME, cls.SQL_INDEXES)
        print("\tcreated.")
