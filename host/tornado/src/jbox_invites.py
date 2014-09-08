import boto.dynamodb.exceptions
import datetime, pytz

from jbox_util import log_info, CloudHelper

class JBoxInvite():
    NAME = None
    SCHEMA = None
    CONN = None
    TABLE = None

    def __init__(self, invite_code, invited=None, create=False):
        if None == JBoxInvite.TABLE:
            return
        self.item = None
        try:
            self.item = JBoxInvite.TABLE.get_item(invite_code)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError as nfe:
            if create:
                if len(invite_code) < 6:
                    raise(Exception("Invite code is too short. Must be at least 6 chars."))
                self.item = JBoxInvite.TABLE.new_item(hash_key=invite_id)
                self.item['time_created'] = datetime.datetime.now(pytz.utc).isoformat()
                self.item['invited'] = invited
                self.is_new = True
            else:
                raise

    def save(self):
        if None == JBoxInvite.TABLE:
            return        
        self.item['time_updated'] = datetime.datetime.now(pytz.utc).isoformat()
        self.item.put()

    def delete(self):
        if None == JBoxInvite.TABLE:
            return        
        self.item.delete()

    def is_invited(self, user_id):
        if None == JBoxInvite.TABLE:
            return        
        if not self.item: return
        if self.item['invited'] is None: return False
        if self.item['invited'] == '*': # Anyone is allowed
            return True
        ids = map(str.strip, self.item['invited'].split(","))
        return user_id in ids

    @staticmethod
    def _init(table_name='jbox_invites', enckey=None):
        JBoxInvite.NAME = table_name
        
        if JBoxInvite.CONN == None:
            JBoxInvite.CONN = CloudHelper.connect_dynamodb()            
            if None != JBoxInvite.CONN:
                JBoxInvite.SCHEMA = JBoxInvite.CONN.create_schema(hash_key_name='invite_code', hash_key_proto_value=str)
                JBoxInvite.TABLE = JBoxInvite.CONN.table_from_schema(name=JBoxInvite.NAME, schema=JBoxInvite.SCHEMA)
                #JBoxInvite.TABLE = JBoxInvite.CONN.get_table(JBoxInvite.NAME)
        log_info("JBoxInvite initialized")

    @staticmethod
    def _create_table():
        JBoxInvite.TABLE = JBoxInvite.CONN.create_table(name=JBoxInvite.NAME, schema=JBoxInvite.SCHEMA, read_units=1, write_units=1)
        log_info("JBoxInvite created")

