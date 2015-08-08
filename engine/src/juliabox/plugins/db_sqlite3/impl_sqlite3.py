__author__ = 'tan'

import threading
import sqlite3

from juliabox.db import JBPluginDB, JBoxDBItemNotFound
from juliabox.jbox_util import JBoxCfg, LoggerMixin


class JBoxSQLiteTable(LoggerMixin):
    OP = {
        'eq': (' = ?', lambda x: x),
        'ne': (' != ?', lambda x: x),
        'le': (' <= ?', lambda x: x),
        'lt': (' < ?', lambda x: x),
        'ge': (' >= ?', lambda x: x),
        'gt': (' > ?', lambda x: x),
        'beginswith': (' like ?', lambda x: x + '%'),
        'between': (' between ? and ?', lambda x: x)
    }

    def __init__(self, table_name):
        self.name = table_name
        c = JBoxSQLite3.conn().cursor()
        pragma_sql = 'pragma table_info("%s")' % (table_name,)
        c.execute(pragma_sql)
        rows = c.fetchall()
        pragma_cols = [spec[0] for spec in c.description]

        columns = []
        pk = []
        for row in rows:
            rowdict = dict(zip(pragma_cols, row))
            colname = rowdict['name']
            columns.append(colname)
            if rowdict['pk'] == 1:
                pk.append(colname)
        c.close()
        self.columns = columns
        self.pk = pk
        self.insert_statement = "insert into " + table_name + \
                                " (" + ", ".join(self.columns) + ")" + \
                                " values (" + ", ".join(['?'] * len(self.columns)) + ")"

    def insert(self, record):
        values = []
        for colname in self.columns:
            values.append(record[colname] if colname in record else None)
        c = JBoxSQLite3.conn().cursor()
        c.execute(self.insert_statement, tuple(values))
        c.close()
        self.commit()

    @staticmethod
    def _op(name, opstr, value, names, values):
        namestr, valsf = JBoxSQLiteTable.OP[opstr]
        vals = valsf(value)
        names.append(name + namestr)
        if isinstance(vals, (list, tuple)):
            values.extend(vals)
        else:
            values.append(vals)

    def _select(self, count, **kwargs):
        names = []
        values = []
        for (n, v) in kwargs.iteritems():
            ncomps = n.split('__')
            colname = ncomps[0]
            if colname not in self.columns:
                continue
            op = ncomps[1] if len(ncomps) > 1 else "eq"
            JBoxSQLiteTable._op(colname, op, v, names, values)

        selattribs = 'count(*)' if count else '*'
        if len(names) > 0:
            criteria = ' where ' + ' and '.join(names)
        else:
            criteria = ''
        stmt = 'select %s from %s%s' % (selattribs, self.name, criteria)

        c = JBoxSQLite3.conn().cursor()
        c.execute(stmt, tuple(values))
        return c

    def select(self, **kwargs):
        c = self._select(False, **kwargs)
        row = c.fetchone()
        if row is None:
            raise JBoxDBItemNotFound()

        item = dict(zip(self.columns, row))
        c.close()
        return item

    def scan(self, **kwargs):
        c = self._select(False, **kwargs)
        return (dict(zip(self.columns, row)) for row in c)

    def count(self, **kwargs):
        c = self._select(True, **kwargs)
        row = c.fetchone()
        if row is None:
            return 0
        return row[0]

    def delete(self, record):
        names = []
        values = []
        for keyname in self.pk:
            keyval = record.get(keyname, None)
            if keyval is None:
                continue
            names.append("%s = ?" % (keyname,))
            values.append(keyval)

        if len(names) != len(self.pk):
            raise JBoxDBItemNotFound()
        criteria = ' where ' + ' and '.join(names)
        stmt = "delete from %s%s" % (self.name, criteria)

        c = JBoxSQLite3.conn().cursor()
        # self.log_debug("SQL: %s", stmt)
        c.execute(stmt, tuple(values))
        c.close()
        self.commit()

    def update(self, record):
        keynames = []
        updates = []
        values = []

        for keyname in self.columns:
            if keyname in self.pk:
                continue
            keyval = record.get(keyname, None)
            updates.append("%s = ?" % (keyname,))
            values.append(keyval)
        updatecols = ', '.join(updates)

        for keyname in self.pk:
            keyval = record.get(keyname, None)
            if keyval is None:
                continue
            keynames.append("%s = ?" % (keyname,))
            values.append(keyval)

        if len(keynames) != len(self.pk):
            raise JBoxDBItemNotFound()
        criteria = ' where ' + ' and '.join(keynames)

        stmt = "update %s set %s%s" % (self.name, updatecols, criteria)

        c = JBoxSQLite3.conn().cursor()
        # self.log_debug("SQL: %s", stmt)
        c.execute(stmt, tuple(values))
        c.close()
        self.commit()

    @staticmethod
    def commit():
        JBoxSQLite3.conn().commit()


class JBoxSQLite3(JBPluginDB):
    provides = [JBPluginDB.JBP_DB, JBPluginDB.JBP_DB_RDBMS]

    threadlocal = threading.local()
    CONNECT_STR = ":memory:" # default to an in-memory database

    @staticmethod
    def configure():
        dbconf = JBoxCfg.get("db")
        JBoxSQLite3.log_debug("db_conf: %r", dbconf)
        if dbconf is not None and 'connect_str' in dbconf:
            JBoxSQLite3.CONNECT_STR = dbconf['connect_str']

    @staticmethod
    def conn():
        c = getattr(JBoxSQLite3.threadlocal, 'sqlite_conn', None)
        if c is None:
            JBoxSQLite3.log_debug("connecting with %s", JBoxSQLite3.CONNECT_STR)
            JBoxSQLite3.threadlocal.sqlite_conn = c = sqlite3.connect(JBoxSQLite3.CONNECT_STR)
        return c

    @staticmethod
    def table_open(tablename):
        return JBoxSQLiteTable(tablename)

    @staticmethod
    def record_create(table, data):
        table.insert(data)

    @staticmethod
    def record_fetch(table, **kwargs):
        return table.select(**kwargs)

    @staticmethod
    def record_scan(table, **kwargs):
        return table.scan(**kwargs)

    @staticmethod
    def record_query(table, **kwargs):
        return table.scan(**kwargs)

    @staticmethod
    def record_count(table, **kwargs):
        return table.count(**kwargs)

    @staticmethod
    def record_save(table, record):
        table.update(record)

    @staticmethod
    def record_delete(table, record):
        table.delete(record)