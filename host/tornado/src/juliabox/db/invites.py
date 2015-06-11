import datetime
import pytz

from boto.dynamodb2.fields import HashKey
from boto.dynamodb2.types import STRING
import boto.dynamodb2.exceptions
import isodate

from juliabox.db import JBoxDB


class JBoxInvite(JBoxDB):
    NAME = 'jbox_invites'

    SCHEMA = [
        HashKey('invite_code', data_type=STRING)
    ]

    INDEXES = None

    TABLE = None

    def __init__(self, invite_code, invited=None, create=False):
        if self.table() is None:
            return

        self.item = None
        try:
            self.item = self.table().get_item(invite_code=invite_code)
            self.is_new = False
        except boto.dynamodb2.exceptions.ItemNotFound:
            if create:
                if len(invite_code) < 6:
                    raise(Exception("Invite code is too short. Must be at least 6 chars."))
                now = datetime.datetime.now(pytz.utc)
                data = {
                    'invite_code': invite_code,
                    'time_created': now.isoformat(),
                    'expires_on': (now + datetime.datetime.timedelta(1)).isoformat(),  # 1 day
                    'invited': invited
                }
                self.create(data)
                self.item = self.table().get_item(invite_code=invite_code)
                self.is_new = True
            else:
                raise

    def save(self):
        self.set_attrib('time_updated', datetime.datetime.now(pytz.utc).isoformat())
        super(JBoxInvite, self).save()

    def is_invited(self, user_id):
        if (self.table() is None) or (self.item is None):
            return  # is this handled well?

        if self.item.get('invited', None) is None:
            return False

        max_count = self.item.get('max_count', None)
        if max_count is not None and max_count <= self.item.get('count', 0):
            return False

        try:
            expires = isodate.parse_datetime(self.item['expires_on'])
        except:
            self.log_info("Error parsing invite code expiry date: " + str(self.item['invite_id']) +
                          str(self.item['expires_on']))
            return False

        if expires < datetime.datetime.now(pytz.utc):
            # This invite code has expired, and hence invalid
            return False
        if self.item['invited'] == '*':  # Anyone is allowed
            return True

        ids = map(str.strip, self.item['invited'].split(","))
        return user_id in ids

    def increment_count(self):
        if (self.table() is None) or (self.item is None):
            return  # is this handled well?

        c = self.item.get('count', 0)
        self.item['count'] = c + 1
