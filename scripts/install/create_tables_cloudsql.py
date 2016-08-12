#! /usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "engine", "src"))

import MySQLdb
import time

from juliabox.db import JBoxUserV2, JBoxDynConfig, JBoxSessionProps, JBoxInstanceProps, JBPluginDB, JBoxAPISpec, JBoxUserProfile
from juliabox.jbox_util import JBoxCfg

# import any plugins that contribute tables
import juliabox.plugins.course_homework
import juliabox.plugins.usage_accounting

def table_exists(table_name):
    try:
        c.execute("select * from %s where 1=0" % (table_name,))
        c.fetchall()
        return c.description is not None
    except:
        return False

def table_create(table_name, columns=None, types=None, keys=None, keys_types=None):
    stmt = []
    if keys is not None:
        for k, t in zip(keys, keys_types):
            stmt.append('`' + k + '` ' + t)
    if columns is not None:
        for col, t in zip(columns, types):
            stmt.append('`' + col + '` ' + t)
    sql = 'create table `%s` (%s' % (table_name, ', '.join(stmt))
    if keys is not None:
        sql += (', primary key (%s)' % (', '.join(keys),))
    sql += ')'
    c.execute(sql)
    conn.commit()

def index_exists(tname, iname):
    f = c.execute("show index from `%s` where Key_name=\"%s\"" % (tname, iname))
    return f is not 0

def indexes_create(table_name, indexes):
    if indexes == None:
        print("No indexes to create")
        return
    for idx in indexes:
        name = idx['name']
        if index_exists(table_name, name):
            print("Index %s already exists" % name)
        else:
            cols = ', '.join('`' + col + '`' for col in idx['cols'])
            sql = "CREATE INDEX `%s` ON `%s`(%s)" % (name, table_name, cols)
            c.execute(sql)
            conn.commit()
            print("Created index %s" & name)

def get_connection():
    # Copy from /jboxengine/conf/jbox.user
    conf = None
    with open('/jboxengine/conf/jbox.user') as f:
        conf = eval(f.read())
    db = conf['db']
    user = db['user']
    passwd = db['passwd']
    unix_socket = db['unix_socket']
    db = db['db']
    return MySQLdb.connect(user=user, passwd=passwd, db=db, unix_socket=unix_socket)

conn = get_connection()
c = conn.cursor()

tables = [JBoxUserV2, JBoxDynConfig, JBoxSessionProps, JBoxInstanceProps, JBoxAPISpec, JBoxUserProfile]
for plugin in JBPluginDB.jbox_get_plugins(JBPluginDB.JBP_TABLE_DYNAMODB):
    tables.append(plugin)

for cls in tables:
    print("Creating %s..." % (cls.NAME,))
    if table_exists(cls.NAME):
        print("\texists already!")
    else:
        table_create(cls.NAME, cls.ATTRIBUTES, cls.TYPES, cls.KEYS, cls.KEYS_TYPES)
        print("\tcreated.")

for cls in tables:
    print("Creating indexes for %s..." % (cls.NAME))
    indexes_create(cls.NAME, cls.SQL_INDEXES)

print('Creating scale_up_time')
if table_exists('scale_up_time'):
    print('\texists already!')
else:
    table_create('scale_up_time', ['scale_up_time'], ['INT'])
    c.execute('INSERT INTO scale_up_time (scale_up_time) VALUES (%d)' % int(time.time()))
    conn.commit()
    print('\tcreated.')

print('Creating mails')
if table_exists('mails'):
    print('\texists already!')
else:
    table_create('mails', ['rcpt', 'sender', 'timestamp'],
                 ['VARCHAR(200)', 'VARCHAR(200)', 'INT'])
    print('\tcreated.')
