import boto.dynamodb.exceptions
import datetime, pytz
from jbox_util import log_info, CloudHelper
from jbox_crypto import encrypt, decrypt

class JBoxUser():
    NAME = None
    SCHEMA = None
    CONN = None
    TABLE = None
    ENCKEY = None
        
    def __init__(self, user_id, create=False, verified=0):
        if None == JBoxUser.TABLE:
            self.is_new = False
            return
        
        try:
            self.item = JBoxUser.TABLE.get_item(user_id)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError as nfe:
            if create:
                self.item = JBoxUser.TABLE.new_item(hash_key=user_id)
                self.item['time_created'] = datetime.datetime.now(pytz.utc).isoformat()
                self.item['verified'] = verified
                self.is_new = True
            else:
                raise
    
    def save(self):
        if None == JBoxUser.TABLE:
            return        
        self.item['time_updated'] = datetime.datetime.now(pytz.utc).isoformat()
        self.item.put()
    
    def delete(self):
        if None == JBoxUser.TABLE:
            return        
        self.item.delete()
    
    def set_gtok(self, gtok):
        if None == JBoxUser.TABLE:
            return        
        self.item['gtok'] = encrypt(gtok, JBoxUser.ENCKEY)

    def set_verified(self, verified=1):
        if JBoxUser.TABLE is None:
            return        
        self.item['verified'] = verified

    def get_verified(self, verified=True):
        if JBoxUser.TABLE is None:
            return
        return self.item['verified'] if self.item.has_key('verified') else 0

    def get_gtok(self):
        if None == JBoxUser.TABLE:
            return None
        gtok = self.item.get('gtok', None)
        if gtok == None:
            return None
        return decrypt(gtok, JBoxUser.ENCKEY)
    
    @staticmethod
    def _init(table_name='jbox_users', enckey=None):
        JBoxUser.NAME = table_name
        
        if JBoxUser.ENCKEY == None:
            JBoxUser.ENCKEY = enckey
            
        if JBoxUser.CONN == None:
            JBoxUser.CONN = CloudHelper.connect_dynamodb()            
            if None != JBoxUser.CONN:
                JBoxUser.SCHEMA = JBoxUser.CONN.create_schema(hash_key_name='user_id', hash_key_proto_value=str)
                JBoxUser.TABLE = JBoxUser.CONN.table_from_schema(name=JBoxUser.NAME, schema=JBoxUser.SCHEMA)
                #JBoxUser.TABLE = JBoxUser.CONN.get_table(JBoxUser.NAME)
        log_info("JBoxUser initialized")

    @staticmethod
    def _create_table():
        JBoxUser.TABLE = JBoxUser.CONN.create_table(name=JBoxUser.NAME, schema=JBoxUser.SCHEMA, read_units=1, write_units=1)
        log_info("JBoxUser created")
        
