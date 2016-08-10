import datetime
import pytz
import json

from boto.dynamodb2.fields import HashKey, RangeKey, GlobalKeysOnlyIndex
from boto.dynamodb2.types import NUMBER, STRING

from juliabox.db import JBoxDB, JBoxDBItemNotFound


class JBoxUserProfile(JBoxDB):
    NAME = 'jbox_user_profiles'

    SCHEMA = [
        HashKey('user_id', data_type=STRING)
    ]

    INDEXES = [
        GlobalKeysOnlyIndex('create_month-create_time-index', parts=[
            HashKey('create_month', data_type=NUMBER),
            RangeKey('create_time', data_type=NUMBER)
        ]),
        GlobalKeysOnlyIndex('update_month-update_time-index', parts=[
            HashKey('update_month', data_type=NUMBER),
            RangeKey('update_time', data_type=NUMBER)
        ])
    ]

    TABLE = None

    ATTR_FIRST_NAME = 'first_name'
    ATTR_LAST_NAME = 'last_name'
    ATTR_COUNTRY = 'country'
    ATTR_CITY = 'city'
    ATTR_LOCATION = 'location'          # a fuzzy location string, indicative of country and city
    ATTR_IP = 'ip'                      # ip from which last accessed
    ATTR_INDUSTRY = 'industry'
    ATTR_ORGANIZATION = 'org'           # workplace
    ATTR_ORG_TITLE = 'org_title'        # job title

    KEYS = ['user_id']
    ATTRIBUTES = ['create_month', 'create_time', 'update_month', 'update_time',
                  ATTR_FIRST_NAME, ATTR_LAST_NAME,
                  ATTR_COUNTRY, ATTR_CITY, ATTR_LOCATION, ATTR_IP,
                  ATTR_INDUSTRY, ATTR_ORGANIZATION, ATTR_ORG_TITLE,
                  'sources'  # a JSON field that indicates where each profile attribute was filled from
                  ]
    SQL_INDEXES = [
        {'name': 'create_month-create_time-index',
         'cols': ['create_month', 'create_time']},
        {'name': 'update_month-update_time-index',
         'cols': ['update_month', 'update_time']},
        {'name': 'activation_code-activation_status-index',
         'cols': ['activation_code', 'activation_status']},
    ]
    KEYS_TYPES = [JBoxDB.VCHAR]
    TYPES = [JBoxDB.INT, JBoxDB.INT, JBoxDB.INT, JBoxDB.INT,
             JBoxDB.VCHAR, JBoxDB.VCHAR,
             JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.VCHAR,
             JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.VCHAR,
             JBoxDB.VCHAR]

    SRC_USER = 1            # filled in by the user
    SRC_DERIVED = 2         # derived from other fields

    def __init__(self, user_id, create=False):
        try:
            self.item = self.fetch(user_id=user_id)
            self.is_new = False
        except JBoxDBItemNotFound:
            if create:
                data = {
                    'user_id': user_id
                }
                JBoxUserProfile._set_time(data, "create")
                self.create(data)
                self.item = self.fetch(user_id=user_id)
                self.is_new = True
            else:
                raise

    def get_user_id(self):
        return self.get_attrib('user_id')

    def get_attrib_source(self, attrib_name):
        sources_str = self.get_attrib('sources', '{}')
        if len(sources_str) == 0:
            return None
        sources = json.loads(sources_str)
        return sources[attrib_name] if attrib_name in sources else None

    def set_attrib_source(self, attrib_name, source):
        sources_str = self.get_attrib('sources', '{}')
        if len(sources_str) == 0:
            sources_str = '{}'
        sources = json.loads(sources_str)
        sources[attrib_name] = source
        self.set_attrib('sources', json.dumps(sources))

    def is_set_by_user(self, attrib_name):
        return self.get_attrib_source(attrib_name) == JBoxUserProfile.SRC_USER

    def set_profile(self, attrib_name, value, source):
        # do not overwrite attributes set by the user
        if source != JBoxUserProfile.SRC_USER and self.is_set_by_user(attrib_name):
            return False
        self.set_attrib(attrib_name, value)
        self.set_attrib_source(attrib_name, source)
        return True

    def can_set(self, attrib_name, value):
        if value is None or len(value) == 0:
            return False
        return value != self.get_attrib(attrib_name)

    def get_profile(self, attrib_name, default=''):
        return self.get_attrib(attrib_name, default)

    def set_time(self, prefix, dt=None):
        JBoxUserProfile._set_time(self.item, prefix, dt)

    @staticmethod
    def _set_time(item, prefix, dt=None):
        if dt is None:
            dt = datetime.datetime.now(pytz.utc)

        if prefix not in ["create", "update"]:
            raise (Exception("invalid prefix for setting time"))

        item[prefix + "_month"] = JBoxUserProfile.datetime_to_yyyymm(dt)
        item[prefix + "_time"] = JBoxUserProfile.datetime_to_epoch_secs(dt)

    def get_time(self, prefix):
        if prefix not in ["create", "update"]:
            raise (Exception("invalid prefix for setting time"))
        return JBoxUserProfile.epoch_secs_to_datetime(self.item[prefix + "_time"])

    def save(self, set_time=True):
        self.set_time("update")
        super(JBoxUserProfile, self).save()
