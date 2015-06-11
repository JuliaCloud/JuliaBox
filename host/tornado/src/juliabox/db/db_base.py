import datetime
import pytz

from boto.dynamodb2.table import Table

from juliabox.cloud.aws import CloudHost
from juliabox.jbox_util import LoggerMixin, JBoxCfg, JBoxPluginType


class JBoxDB(LoggerMixin):
    @classmethod
    def table(cls):
        if (cls.TABLE is None) and (CloudHost.ENABLED['dynamodb']) and (cls.NAME is not None):
            cls.TABLE = Table(cls.NAME)
            cls.log_info(cls.__name__ + " initialized to " + cls.NAME)
        return cls.TABLE

    @classmethod
    def create(cls, data):
        if not cls.table().put_item(data=data):
            raise Exception("Error creating record")

    def save(self):
        cls = self.__class__
        if cls.TABLE is None:
            return
        self.item.save()

    def delete(self):
        cls = self.__class__
        if cls.TABLE is None:
            return
        self.item.delete()

    def get_attrib(self, name, default=None):
        if self.item is not None:
            return self.item.get(name, default)
        else:
            return None

    def set_attrib(self, name, value):
        if self.item is not None:
            self.item[name] = value

    def del_attrib(self, name):
        if (self.item is not None) and (name in self.item):
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
    - dynamodb.table (tables hosted on dynamodb)

    Plugins are expected to have:
    - NAME: attribute holding table name
    - SCHEMA and INDEXES: attributes holding table structure
    - TABLE: attribute to hold the table reference

    Plugins can take help of base methods provided in JBoxDB.
    """

    __metaclass__ = JBoxPluginType