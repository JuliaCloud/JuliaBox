__author__ = 'tan'
import datetime
import pytz

from boto.dynamodb2.fields import HashKey, RangeKey, GlobalKeysOnlyIndex
from boto.dynamodb2.types import STRING

from juliabox.db import JBoxDB, JBoxDBItemNotFound


class JBoxAPISpec(JBoxDB):
    NAME = 'jbox_apispec'

    SCHEMA = [
        HashKey('api_name', data_type=STRING)
    ]

    INDEXES = [
        GlobalKeysOnlyIndex('publisher-api_name-index', parts=[
            HashKey('publisher', data_type=STRING),
            RangeKey('api_name', data_type=STRING)
        ])
    ]

    TABLE = None

    KEYS = ['api_name']
    ATTRIBUTES = ['publisher', 'cmd', 'image_name', 'description',
                  'timeout_secs', 'create_time']
    SQL_INDEXES = [
        {'name': 'publisher-api_name-index', 'cols': ['publisher', 'api_name']}
    ]
    KEYS_TYPES = [JBoxDB.VCHAR]
    TYPES = [JBoxDB.VCHAR, JBoxDB.TEXT, JBoxDB.VCHAR, JBoxDB.VCHAR,
             JBoxDB.INT, JBoxDB.INT]

    def __init__(self, api_name, cmd=None, image_name=None, description=None,
                 publisher=None, timeout_secs=None, create=False):
        try:
            self.item = self.fetch(api_name=api_name)
            self.is_new = False
        except JBoxDBItemNotFound:
            if create:
                dt = datetime.datetime.now(pytz.utc)
                data = {
                    'api_name': api_name,
                    'cmd': cmd,
                    'description': description,
                    'publisher': publisher,
                    'create_time': JBoxAPISpec.datetime_to_epoch_secs(dt)
                }
                if image_name is not None:
                    data['image_name'] = image_name
                if timeout_secs is not None:
                    data['timeout_secs'] = timeout_secs

                self.create(data)
                self.item = self.fetch(api_name=api_name)
                self.is_new = True
            else:
                raise

    def get_api_name(self):
        return self.get_attrib('api_name', None)

    def get_timeout_secs(self):
        return int(self.get_attrib('timeout_secs', 30))

    def get_description(self):
        return self.get_attrib('description', None)

    def get_publisher(self):
        return self.get_attrib('publisher', None)

    def get_image_name(self):
        return self.get_attrib('image_name', 'juliabox/juliaboxapi:latest')

    def get_cmd(self):
        return self.get_attrib('cmd', None)

    def get_create_time(self):
        return int(self.get_attrib('create_time', None))

    def set_cmd(self, cmd):
        self.set_attrib('cmd', cmd)

    def set_description(self, description):
        self.set_attrib('description', description)

    def set_timeout_secs(self, timeout_secs):
        self.set_attrib('timeout_secs', timeout_secs)

    def set_publisher(self, publisher):
        self.set_attrib('publisher', publisher)

    def set_image_name(self, image_name):
        self.set_attrib('image_name', image_name)

    def as_json(self):
        def _add_not_none(d, n, v):
            if v is not None:
                d[n] = v

        jsonval = dict()
        _add_not_none(jsonval, 'api_name', self.get_api_name())
        _add_not_none(jsonval, 'cmd', self.get_cmd())
        _add_not_none(jsonval, 'image_name', self.get_image_name())
        _add_not_none(jsonval, 'description', self.get_description())
        _add_not_none(jsonval, 'publisher', self.get_publisher())
        _add_not_none(jsonval, 'timeout_secs', self.get_timeout_secs())
        _add_not_none(jsonval, 'create_time', self.get_create_time())
        return jsonval

    @staticmethod
    def get_api_info(publisher, api_name):
        if publisher is None and api_name is None:
            raise
        ret = []
        if publisher is None:
            ret.append(JBoxAPISpec(api_name).as_json())
        else:
            if api_name is None:
                api_name = ' '
            records = JBoxAPISpec.query(publisher__eq=publisher, api_name__gte=api_name,
                                        index='publisher-api_name-index')
            for api in records:
                ret.append(JBoxAPISpec(api['api_name']).as_json())
        return ret

    @staticmethod
    def set_api_info(api_name, cmd=None, image_name=None, description=None, publisher=None, timeout_secs=None):
        try:
            api = JBoxAPISpec(api_name)
            if cmd is not None:
                api.set_cmd(cmd)
            if image_name is not None:
                api.set_image_name(image_name)
            if description is not None:
                api.set_description(description)
            if publisher is not None:
                api.set_publisher(publisher)
            if timeout_secs is not None:
                api.set_timeout_secs(timeout_secs)
            api.save()
        except JBoxDBItemNotFound:
            JBoxAPISpec(api_name, cmd=cmd, image_name=image_name, description=description, publisher=publisher,
                        timeout_secs=timeout_secs, create=True)
