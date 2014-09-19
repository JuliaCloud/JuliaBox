import boto.dynamodb.exceptions
import datetime
import isodate
import pytz

from db.db_base import JBoxDB


class JBoxInvite(JBoxDB):
    NAME = 'jbox_invites'
    TABLE = None

    def __init__(self, invite_code, invited=None, create=False):
        if self.table() is None:
            return

        self.item = None
        try:
            self.item = self.table().get_item(invite_code)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError:
            if create:
                if len(invite_code) < 6:
                    raise(Exception("Invite code is too short. Must be at least 6 chars."))
                self.item = JBoxInvite.TABLE.new_item(hash_key=invite_code)
                now = datetime.datetime.now(pytz.utc)
                self.item['time_created'] = now.isoformat()
                self.item['expires_on'] = (now + datetime.datetime.timedelta(1)).isoformat()  # 1 day
                self.item['invited'] = invited
                self.is_new = True
            else:
                raise

    def save(self):
        if self.item is not None:
            self.item['time_updated'] = datetime.datetime.now(pytz.utc).isoformat()
        super(JBoxInvite, self).save()

    def is_invited(self, user_id):
        if (self.table() is None) or (self.item is None):
            return  # is this handled well?

        if self.item.get('invited', None):
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
