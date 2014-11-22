import datetime, pytz
from cloud.aws import CloudHost

from jbox_util import LoggerMixin


class JBoxDB(LoggerMixin):
    CONN = None
    ENCKEY = None

    @classmethod
    def conn(cls):
        if JBoxDB.CONN is None:
            JBoxDB.CONN = CloudHost.connect_dynamodb()
            cls.log_info("DB connected: " + str(JBoxDB.CONN is not None))
        return JBoxDB.CONN

    @classmethod
    def table(cls):
        if (cls.TABLE is None) and (cls.conn() is not None) and (cls.NAME is not None):
            cls.TABLE = cls.conn().get_table(cls.NAME)
            cls.log_info(cls.__name__ + " initialized to " + cls.NAME)
        return cls.TABLE

    def save(self):
        cls = self.__class__
        if cls.TABLE is None:
            return
        self.item.put()

    def delete(self):
        cls = self.__class__
        if cls.TABLE is None:
            return
        self.item.delete()

    @classmethod
    def enckey(cls):
        return JBoxDB.ENCKEY

    @staticmethod
    def configure(cfg):
        JBoxDB.ENCKEY = cfg['sesskey']

    @staticmethod
    def datetime_to_yyyymm(dt):
        return dt.year*100 + dt.month

    @staticmethod
    def datetime_to_yyyymmdd(dt):
        return dt.year*10000 + dt.month*100 + dt.day

    @staticmethod
    def datetime_to_epoch_secs(dt):
        epoch = datetime.datetime.fromtimestamp(0, pytz.utc)
        return (dt - epoch).total_seconds()

    @staticmethod
    def epoch_secs_to_datetime(secs):
        epoch = datetime.datetime.fromtimestamp(0, pytz.utc)
        return epoch + datetime.timedelta(seconds=secs)
