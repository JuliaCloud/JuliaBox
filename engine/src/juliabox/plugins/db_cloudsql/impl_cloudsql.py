__author__ = 'Nishanth'

import threading
import MySQLdb
import decimal
import copy

from juliabox.db import JBPluginDB, JBoxDBItemNotFound
from juliabox.jbox_util import JBoxCfg, LoggerMixin


class JBoxMySQLTable(LoggerMixin):
    OP = {
        'eq': (' = %%(%s)s', lambda x: x),
        'ne': (' != %%(%s)s', lambda x: x),
        'lte': (' <= %%(%s)s', lambda x: x),
        'lt': (' < %%(%s)s', lambda x: x),
        'gte': (' >= %%(%s)s', lambda x: x),
        'gt': (' > %%(%s)s', lambda x: x),
        'beginswith': (' like %%(%s)s', lambda x: x + '%'),
        'between': (' between %%(%s)s and %%(%s)s', lambda x: x)
    }

    def __init__(self, table_name):
        self.name = table_name
        pragma_sql = 'show columns from %s' % (table_name,)
        c = JBoxCloudSQL.execute(pragma_sql)
        rows = c.fetchall()
        pragma_cols = [spec[0] for spec in c.description]

        columns = []
        pk = []
        for row in rows:
            rowdict = dict(zip(pragma_cols, row))
            colname = rowdict['Field']
            columns.append(colname)
            if rowdict['Key'] == 'PRI':
                pk.append(colname)
        c.close()
        self.columns = columns
        self.pk = pk
        params = []
        for col in columns:
            params.append('%('+ col +')s')
        self.insert_statement = "insert into " + table_name + \
                                " (" + ", ".join(self.columns) + ")" + \
                                " values (" + ", ".join(params) + ")"

    def insert(self, record_):
        record = copy.deepcopy(record_)
        for col in self.columns:
            if col not in record.keys():
                record[col] = None
        c = JBoxCloudSQL.execute(self.insert_statement, record)
        c.close()

    @staticmethod
    def _op(name, opstr, value, names, values):
        namestr, valsf = JBoxMySQLTable.OP[opstr]
        vals = valsf(value)
        if opstr == 'between':
            names.append(name + (namestr % (name + 'L', name + 'R') ))
        else:
            names.append(name + (namestr % name))
        if isinstance(vals, (list, tuple)):
            values.extend(vals)
        else:
            values.append(vals)

    def _select(self, count, **kwargs):
        names = []
        values = []
        colnames = []

        use_index_sql = ''
        use_index = kwargs.get('index')
        if use_index:
            use_index_sql = ' use index (`%s`) ' % use_index

        for (n, v) in kwargs.iteritems():
            ncomps = n.split('__')
            colname = ncomps[0]
            if colname not in self.columns:
                continue
            op = ncomps[1] if len(ncomps) > 1 else "eq"
            JBoxMySQLTable._op(colname, op, v, names, values)
            if op == 'between':
                colnames.extend((colname + 'L', colname + 'R'))
            else:
                colnames.append(colname)

        selattribs = 'count(*)' if count else '*'
        if len(names) > 0:
            criteria = ' where ' + ' and '.join(names)
        else:
            criteria = ''
        stmt = 'select %s from %s%s%s' % (selattribs, self.name,
                                          use_index_sql, criteria)
        params = dict(zip(colnames, values))
        c = JBoxCloudSQL.execute(stmt, params)
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
        colnames = []
        for keyname in self.pk:
            keyval = record.get(keyname, None)
            if keyval is None:
                continue
            names.append("%s = %%(%s)s" % (keyname, keyname))
            values.append(keyval)
            colnames.append(keyname)

        if len(names) != len(self.pk):
            raise JBoxDBItemNotFound()
        criteria = ' where ' + ' and '.join(names)
        stmt = "delete from %s%s" % (self.name, criteria)

        # self.log_debug("SQL: %s", stmt)
        c = JBoxCloudSQL.execute(stmt, dict(zip(colnames, values)))
        c.close()

    def update(self, record):
        keynames = []
        updates = []
        values = []
        names = []

        for keyname in self.columns:
            if keyname in self.pk:
                continue
            keyval = record.get(keyname, None)
            updates.append("%s = %%(%s)s" % (keyname, keyname))
            values.append(keyval)
            names.append(keyname)
        updatecols = ', '.join(updates)

        for keyname in self.pk:
            keyval = record.get(keyname, None)
            if keyval is None:
                continue
            keynames.append("%s = %%(%s)s" % (keyname, keyname))
            values.append(keyval)
            names.append(keyname)

        if len(keynames) != len(self.pk):
            raise JBoxDBItemNotFound()
        criteria = ' where ' + ' and '.join(keynames)

        stmt = "update %s set %s%s" % (self.name, updatecols, criteria)

        # self.log_debug("SQL: %s", stmt)
        c = JBoxCloudSQL.execute(stmt, dict(zip(names, values)))
        c.close()

class JBoxCloudSQL(JBPluginDB):
    provides = [JBPluginDB.JBP_DB, JBPluginDB.JBP_DB_CLOUDSQL]

    threadlocal = threading.local()
    USER = None
    PASSWD = None
    UNIX_SOCKET = None
    DB = None

    @staticmethod
    def configure():
        dbconf = JBoxCfg.get("db")
        JBoxCloudSQL.log_debug("db_conf: %r", dbconf)
        if dbconf is not None:
            JBoxCloudSQL.USER = dbconf['user']
            JBoxCloudSQL.PASSWD = dbconf['passwd']
            JBoxCloudSQL.UNIX_SOCKET = dbconf['unix_socket']
            JBoxCloudSQL.DB = dbconf['db']

    @staticmethod
    def conn(reconnect=False):
        c = getattr(JBoxCloudSQL.threadlocal, 'cloudsql_conn', None)
        if c is None or reconnect:
            JBoxCloudSQL.log_debug("connecting with %s", JBoxCloudSQL.USER)
            JBoxCloudSQL.threadlocal.cloudsql_conn = c = MySQLdb.connect(
                user=JBoxCloudSQL.USER, passwd=JBoxCloudSQL.PASSWD,
                unix_socket=JBoxCloudSQL.UNIX_SOCKET, db=JBoxCloudSQL.DB)
            c.autocommit(True)
        return c

    @staticmethod
    def execute(sql, params=None):
        try:
            cursor = JBoxCloudSQL.conn().cursor()
            cursor.execute(sql, params)
        except (AttributeError, MySQLdb.OperationalError):
            cursor = JBoxCloudSQL.conn(reconnect=True).cursor()
            cursor.execute(sql, params)
        return cursor

    @staticmethod
    def table_open(tablename):
        return JBoxMySQLTable(tablename)

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
