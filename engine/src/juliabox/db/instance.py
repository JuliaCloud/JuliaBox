import json
import datetime
import pytz

from boto.dynamodb2.fields import HashKey
from boto.dynamodb2.types import STRING

from juliabox.db import JBoxDB, JBoxDBItemNotFound


class JBoxInstanceProps(JBoxDB):
    NAME = 'jbox_instance'

    SCHEMA = [
        HashKey('instance_id', data_type=STRING)
    ]

    INDEXES = None

    TABLE = None

    KEYS = ['instance_id']
    ATTRIBUTES = ['load', 'accept', 'api_status', 'publish_time']
    SQL_INDEXES = None
    KEYS_TYPES = [JBoxDB.VCHAR]
    TYPES = [JBoxDB.VCHAR, JBoxDB.INT, JBoxDB.TEXT, JBoxDB.INT]

    # maintenance runs are once in 5 minutes
    # TODO: make configurable
    SESS_UPDATE_INTERVAL = (5 * 1.5) * 60

    def __init__(self, instance_id, create=False):
        try:
            self.item = self.fetch(instance_id=instance_id)
            self.is_new = False
        except JBoxDBItemNotFound:
            if create:
                data = {
                    'instance_id': instance_id
                }
                self.create(data)
                self.item = self.fetch(instance_id=instance_id)
                self.is_new = True
            else:
                raise

    def get_load(self):
        return self.get_attrib('load', '0.0')

    def set_load(self, load):
        self.set_attrib('load', str(load))

    def get_accept(self):
        return self.get_attrib('accept', 0) == 1

    def set_accept(self, accept):
        self.set_attrib('accept', 1 if accept else 0)

    def get_api_status(self):
        try:
            return json.loads(self.get_attrib('api_status', '{}'))
        except:
            return dict()

    def set_api_status(self, api_status):
        self.set_attrib('api_status', json.dumps(api_status))

    def set_publish_time(self):
        now = datetime.datetime.now(pytz.utc)
        self.set_attrib('publish_time', JBoxInstanceProps.datetime_to_epoch_secs(now))

    def get_publish_time(self):
        now = datetime.datetime.now(pytz.utc)
        return int(self.get_attrib('publish_time', JBoxInstanceProps.datetime_to_epoch_secs(now)))

    @staticmethod
    def set_props(instance_id, load=None, accept=None, api_status=None):
        instance_props = JBoxInstanceProps(instance_id, create=True)
        if load is not None:
            instance_props.set_load(load)
        if accept is not None:
            instance_props.set_accept(accept)
        if api_status is not None:
            instance_props.set_api_status(api_status)
        instance_props.set_publish_time()
        instance_props.save()

    @staticmethod
    def purge_stale_instances():
        for iid in JBoxInstanceProps.get_stale_instances():
            instance = JBoxInstanceProps(iid)
            instance.delete()

    @staticmethod
    def get_stale_instances():
        now = datetime.datetime.now(pytz.utc)
        nowsecs = JBoxInstanceProps.datetime_to_epoch_secs(now)
        valid_time = nowsecs - JBoxInstanceProps.SESS_UPDATE_INTERVAL
        stale = []
        for record in JBoxInstanceProps.scan(publish_time__lt=valid_time):
            stale.append(record.get('instance_id'))
        return stale

    @staticmethod
    def get_instance_status():
        now = datetime.datetime.now(pytz.utc)
        nowsecs = JBoxInstanceProps.datetime_to_epoch_secs(now)
        valid_time = nowsecs - JBoxInstanceProps.SESS_UPDATE_INTERVAL
        result = dict()
        for record in JBoxInstanceProps.scan(publish_time__gte=valid_time):
            iid = record.get('instance_id')
            props = {
                'load': float(record.get('load', '0.0')),
                'accept': bool(record.get('accept', 0)),
                'api_status': json.loads(record.get('api_status', '{}'))
            }
            result[iid] = props
        return result

    @staticmethod
    def get_available_instances():
        now = datetime.datetime.now(pytz.utc)
        nowsecs = JBoxInstanceProps.datetime_to_epoch_secs(now)
        valid_time = nowsecs - JBoxInstanceProps.SESS_UPDATE_INTERVAL
        result = list()
        for record in JBoxInstanceProps.scan(publish_time__gte=valid_time, accept__eq=1):
            result.append(record.get('instance_id'))
        return result
