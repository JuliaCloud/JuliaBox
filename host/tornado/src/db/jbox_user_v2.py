import boto.dynamodb.exceptions
import datetime, pytz
from jbox_util import log_info, CloudHelper
from jbox_crypto import encrypt, decrypt

class JBoxUserV2():
    NAME = None
    CONN = None
    TABLE = None
    ENCKEY = None
        
    def __init__(self, user_id, create=False):
        if None == JBoxUserV2.TABLE:
            self.is_new = False
            return
        
        try:
            self.item = JBoxUserV2.TABLE.get_item(user_id)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError as nfe:
            if create:
                self.item = JBoxUserV2.TABLE.new_item(hash_key=user_id)
                self.set_time("create")
                self.is_new = True
            else:
                raise

    def set_time(self, prefix, dt=None):
        if None == dt:
            dt = datetime.datetime.now(pytz.utc)
    
        if prefix not in ["create", "update"]:
            raise(Exception("invalid prefix for setting time"))
        
        self.item[prefix + "_date"] = JBoxUserV2.datetime_to_yyyymmdd(dt)
        self.item[prefix + "_time"] = JBoxUserV2.datetime_to_epoch_secs(dt)
    
    @staticmethod
    def datetime_to_yyyymmdd(dt):
        return str(dt.year*10000 + dt.month*100 + dt.day)
    
    @staticmethod
    def datetime_to_epoch_secs(dt):
        epoch = datetime.datetime.fromtimestamp(0, pytz.utc)
        return (dt - epoch).total_seconds()
    
    @staticmethod
    def epoch_secs_to_datetime(secs):
        epoch = datetime.datetime.fromtimestamp(0, pytz.utc)
        return epoch + datetime.timedelta(seconds=secs)
    
    def save(self):
        if None == JBoxUserV2.TABLE:
            return
        self.set_time("update")
        self.item.put()
    
    def delete(self):
        if None == JBoxUserV2.TABLE:
            return        
        self.item.delete()

    def set_activation_state(self, activation_code, activation_status):
        if JBoxUserV2.TABLE is None:
            return
        self.item['activation_code'] = activation_code
        self.item['activation_status'] = activation_status
    
    def get_activation_state(self):
        if JBoxUserV2.TABLE is None:
            return (None, None)
        return (self.item.get('activation_code', None), self.item.get('activation_status', 1))
    
    def set_gtok(self, gtok):
        if None == JBoxUserV2.TABLE:
            return        
        self.item['gtok'] = encrypt(gtok, JBoxUserV2.ENCKEY)

    def get_gtok(self):
        if None == JBoxUserV2.TABLE:
            return None
        gtok = self.item.get('gtok', None)
        if gtok == None:
            return None
        return decrypt(gtok, JBoxUserV2.ENCKEY)

    def set_container_type(self, image, resource_profile):
        if None == JBoxUserV2.TABLE:
            return None
        self.item['image'] = image
        self.item['resource_profile'] = resource_profile
    
    def get_container_type(self):
        if JBoxUserV2.TABLE is None:
            return (None, None)
        return (self.item.get('image', None), self.item.get('resource_profile', 1))
    
    @staticmethod
    def _init(table_name='jbox_users_v2', enckey=None):
        JBoxUserV2.NAME = table_name
        
        if JBoxUserV2.ENCKEY == None:
            JBoxUserV2.ENCKEY = enckey
            
        if JBoxUserV2.CONN == None:
            JBoxUserV2.CONN = CloudHelper.connect_dynamodb()            
            if None != JBoxUserV2.CONN:
                JBoxUserV2.TABLE = JBoxUserV2.CONN.get_table(JBoxUserV2.NAME)
        log_info("JBoxUserV2 initialized")
