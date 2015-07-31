import datetime
import pytz

from juliabox.jbox_util import LoggerMixin, JBoxCfg, JBoxPluginType


class JBoxDBItemNotFound(Exception):
    pass


class JBoxDB(LoggerMixin):
    DB_IMPL = None

    @staticmethod
    def configure():
        JBoxDB.DB_IMPL = JBoxDBPlugin.jbox_get_plugin(JBoxDBPlugin.PLUGIN_DB)
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


class JBoxDBPlugin(JBoxDB):
    """ The base class for database table providers.
    DynamoDB is the only type of database supported as of now.

    It is a plugin mount point, looking for features:
    - db.table.dynamodb (tables hosted on dynamodb)
    - db.usage.accounting (table that records usage accounting)

    DynamoDB table providers are expected to have:
    - NAME: attribute holding table name
    - SCHEMA and INDEXES: attributes holding table structure
    - TABLE: attribute to hold the table reference

    Usage accounting providers (may be moved later to a separate plugin) are expected to have:
    - record_session_time method:record start and end times of a session
    - get_stats method: provide usage statistics for a given range of dates

    Plugins can take help of base methods provided in JBoxDB.
    """

    PLUGIN_DB = "db"
    PLUGIN_DB_DYNAMODB = "db.dynamodb"
    PLUGIN_DB_RDBMS = "db.rdbms"

    PLUGIN_TABLE = "db.table"
    PLUGIN_DYNAMODB_TABLE = "db.table.dynamodb"
    PLUGIN_RDBMS_TABLE = "db.table.rdbms"

    PLUGIN_USAGE_ACCOUNTING = "db.usage.accounting"

    __metaclass__ = JBoxPluginType