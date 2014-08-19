import boto.dynamodb, boto.dynamodb.exceptions
import datetime, pytz
from jbox_util import log_info
from jbox_crypto import encrypt, decrypt

class JBoxUser():
    NAME = None
    SCHEMA = None
    CONN = None
    TABLE = None
    ENCKEY = None
        
    def __init__(self, user_id, create=False):
        try:
            self.item = JBoxUser.TABLE.get_item(user_id)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError as nfe:
            if create:
                self.item = JBoxUser.TABLE.new_item(hash_key=user_id)
                self.item['time_created'] = datetime.datetime.now(pytz.utc).isoformat()
                self.is_new = True
            else:
                raise
    
    def save(self):
        self.item['time_updated'] = datetime.datetime.now(pytz.utc).isoformat()
        self.item.put()
    
    def delete(self):
        self.item.delete()
    
    def set_gtok(self, gtok):
        self.item['gtok'] = encrypt(gtok, JBoxUser.ENCKEY)
    
    def get_gtok(self):
        gtok = self.item.get('gtok', None)
        if gtok == None:
            return None
        return decrypt(gtok, JBoxUser.ENCKEY)
    
    @staticmethod
    def _init(table_name='jbox_users', enckey=None):
        JBoxUser.NAME = table_name
        if JBoxUser.CONN == None:
            JBoxUser.CONN = boto.dynamodb.connect_to_region('us-east-1')
        if JBoxUser.SCHEMA == None:
            JBoxUser.SCHEMA = JBoxUser.CONN.create_schema(hash_key_name='user_id', hash_key_proto_value=str)
        if JBoxUser.TABLE == None:
            JBoxUser.TABLE = JBoxUser.CONN.table_from_schema(name=JBoxUser.NAME, schema=JBoxUser.SCHEMA)
        if JBoxUser.ENCKEY == None:
            JBoxUser.ENCKEY = enckey
            #JBoxUser.TABLE = JBoxUser.CONN.get_table(JBoxUser.NAME)
        log_info("JBoxUser initialized")

    @staticmethod
    def _create_table():
        JBoxUser.TABLE = JBoxUser.CONN.create_table(name=JBoxUser.NAME, schema=JBoxUser.SCHEMA, read_units=1, write_units=1)
        log_info("JBoxUser created")
        