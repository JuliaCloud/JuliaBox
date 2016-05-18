import datetime
import pytz

from juliabox.jbox_util import LoggerMixin, JBoxCfg, JBoxPluginType


class JBoxDBItemNotFound(Exception):
    pass


class JBoxDB(LoggerMixin):
    DB_IMPL = None
    INT = 'INT'
    VCHAR = 'VARCHAR(200)'
    TEXT = 'TEXT'

    @staticmethod
    def configure():
        JBoxDB.DB_IMPL = JBPluginDB.jbox_get_plugin(JBPluginDB.JBP_DB)
        JBoxDB.DB_IMPL.configure()

    @classmethod
    def table(cls):
        if cls.TABLE is None:
            cls.TABLE = JBoxDB.DB_IMPL.table_open(cls.NAME)
            cls.log_info("%s initialized to %s with %s", cls.__name__, cls.NAME, JBoxDB.DB_IMPL.__name__)
        return cls.TABLE

    @classmethod
    def create(cls, data):
        JBoxDB.DB_IMPL.record_create(cls.table(), data)

    @classmethod
    def fetch(cls, **kwargs):
        return JBoxDB.DB_IMPL.record_fetch(cls.table(), **kwargs)

    @classmethod
    def scan(cls, **kwargs):
        return JBoxDB.DB_IMPL.record_scan(cls.table(), **kwargs)

    @classmethod
    def query(cls, **kwargs):
        return JBoxDB.DB_IMPL.record_query(cls.table(), **kwargs)

    @classmethod
    def query_count(cls, **kwargs):
        return JBoxDB.DB_IMPL.record_count(cls.table(), **kwargs)

    def save(self):
        JBoxDB.DB_IMPL.record_save(self.__class__.table(), self.item)

    def delete(self):
        JBoxDB.DB_IMPL.record_delete(self.__class__.table(), self.item)

    def get_attrib(self, name, default=None):
        attr = self.item.get(name, default)
        return attr if (attr is not None) else default

    def set_attrib(self, name, value):
        self.item[name] = value

    def del_attrib(self, name):
        if name in self.item:
            del self.item[name]

    @classmethod
    def enckey(cls):
        return JBoxCfg.get('sesskey')

    @staticmethod
    def datetime_to_yyyymm(dt):
        return dt.year*100 + dt.month

    @staticmethod
    def datetime_to_yyyymmdd(dt):
        return dt.year*10000 + dt.month*100 + dt.day

    @staticmethod
    def datetime_to_epoch_secs(dt, allow_microsecs=False):
        epoch = datetime.datetime.fromtimestamp(0, pytz.utc)
        if allow_microsecs:
            return (dt - epoch).total_seconds()
        else:
            return int((dt - epoch).total_seconds())

    @staticmethod
    def epoch_secs_to_datetime(secs):
        epoch = datetime.datetime.fromtimestamp(0, pytz.utc)
        return epoch + datetime.timedelta(seconds=secs)


class JBPluginDB(JBoxDB):
    """ Provide database access and database table definitions.

    - `JBPluginDB.JBP_DB`, `JBPluginDB.JBP_DB_DYNAMODB` and `JBPluginDB.JBP_DB_RDBMS`:
        Provide database access. Must implement the following methods.
        - `configure()`: Read and store database configuration.
        - `table_open(table_name)`: Open and return a handle to the named table. Subsequent operations on table shall pass the handle.
        - `record_create(table, data)`: Insert a new record with data (dictionary of column names and values).
        - `record_fetch(table, **kwargs)`: Fetch a single record. Keys passed in kwargs.
        - `record_scan(table, **kwargs)`: Scan all records in the table`. Required attributes passed in kwargs.
        - `record_query(table, **kwargs)`: Fetch one or more records. Selection criteria passed in kwargs.
        - `record_count(table, **kwargs)`: Count matching records. Selection criteria passed in kwargs.
        - `record_save(table, data)`: Update a single record with data (dictionary of column names and values)
        - `record_delete(table, data)`: Delete a single record with keys specified in data (dictionary of column names and values)
    - `JBPluginDB.JBP_TABLE`, `JBPluginDB.JBP_TABLE_DYNAMODB` and `JBPluginDB.JBP_TABLE_RDBMS`:
        Provide a table implementation. Must extend `JBPluginDB` and provide the following attributes:
        - `TABLE`: to hold the opened table handle
        - `SCHEMA`, `INDEXES`: To define a dynamodb table (only if `JBP_TABLE_DYNAMODB` supported)
        - `KEYS`, `ATTRIBUTES`: To define a rdbms table (only if `JBP_TABLE_RDBMS` supported)
    - `JBPluginDB.JBP_USAGE_ACCOUNTING`:
        Record JuliaBox usage data, per user/session and calculate stats.
        Must provide the following methods:
        - `record_session_time(session, image, start_time, end_time)`: Record usage
        - `get_stats(dates)`: Return statistics of JuliaBox usage across dates (list of dates)
    """

    JBP_DB = "db"
    JBP_DB_DYNAMODB = "db.dynamodb"
    JBP_DB_RDBMS = "db.rdbms"
    JBP_DB_CLOUDSQL = "db.cloudsql"

    JBP_TABLE = "db.table"
    JBP_TABLE_DYNAMODB = "db.table.dynamodb"
    JBP_TABLE_RDBMS = "db.table.rdbms"
    JBP_TABLE_CLOUDSQL = "db.table.cloudsql"

    JBP_USAGE_ACCOUNTING = "db.usage.accounting"

    __metaclass__ = JBoxPluginType
