import boto.dynamodb.exceptions
import datetime, pytz
from jbox_util import log_info, CloudHelper
from jbox_crypto import encrypt, decrypt

class JBoxUserV2():
    """
        - user_id (primary hash key)
        
        - create_month (global secondary hash key)
        - create_time (global secondary range index)
        
        - update_month  (global secondary hash key)
        - update_time (global secondary index)
        
        - activation_code (global secondary hash key)
        - activation_status (global secondary range key)
        
        - image (optional: global secondary hash key)
        - resource_profile (optional: global secondary range key)
        
        - status
        - organization
        - system_profile
        - gtok
    """
    NAME = None
    CONN = None
    TABLE = None
    ENCKEY = None
    
    STATUS_ACTIVE = 0
    STATUS_INACTIVE = 1
    
    ACTIVATION_NONE = 0
    ACTIVATION_GRANTED = 1
    ACTIVATION_REQUESTED = 2
    
    RESOURCE_PROFILE_BASIC = 1
        
    def __init__(self, user_id, create=False):
        if None == JBoxUserV2.TABLE:
            self.is_new = False
            return
        
        try:
            self.item = JBoxUserV2.TABLE.get_item(hash_key=user_id)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError as nfe:
            if create:
                self.item = JBoxUserV2.TABLE.new_item(hash_key=user_id)
                self.set_time("create")
                self.is_new = True
            else:
                raise

    def get_user_id(self):
        if None == JBoxUserV2.TABLE:
            return None
        return self.item['user_id']

    def get_status(self):
        if None == JBoxUserV2.TABLE:
            return None
        return self.item.get('status', JBoxUserV2.STATUS_ACTIVE)
    
    def set_status(self, status):
        if None == JBoxUserV2.TABLE:
            return
        self.item['status'] = status

    def set_time(self, prefix, dt=None):
        if None == JBoxUserV2.TABLE:
            return
        if None == dt:
            dt = datetime.datetime.now(pytz.utc)
    
        if prefix not in ["create", "update"]:
            raise(Exception("invalid prefix for setting time"))
        
        self.item[prefix + "_date"] = JBoxUserV2.datetime_to_yyyymm(dt)
        self.item[prefix + "_time"] = JBoxUserV2.datetime_to_epoch_secs(dt)
    
    def get_time(self, prefix):
        if None == JBoxUserV2.TABLE:
            return None
        if prefix not in ["create", "update"]:
            raise(Exception("invalid prefix for setting time"))
        return JBoxUserV2.epoch_secs_to_datetime(self.item[prefix + "_time"])
    
    @staticmethod
    def datetime_to_yyyymm(dt):
        return dt.year*100 + dt.month
    
    @staticmethod
    def datetime_to_epoch_secs(dt):
        epoch = datetime.datetime.fromtimestamp(0, pytz.utc)
        return (dt - epoch).total_seconds()
    
    @staticmethod
    def epoch_secs_to_datetime(secs):
        epoch = datetime.datetime.fromtimestamp(0, pytz.utc)
        return epoch + datetime.timedelta(seconds=secs)
    
    def save(self, set_time=True):
        if None == JBoxUserV2.TABLE:
            return
        if set_time:
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
        if None == JBoxUserV2.TABLE:
            return None
        if JBoxUserV2.TABLE is None:
            return (None, None)
        return (self.item.get('activation_code', ''), self.item.get('activation_status', JBoxUserV2.ACTIVATION_NONE))
    
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
            return
        self.item['image'] = image
        self.item['resource_profile'] = resource_profile
    
    def get_container_type(self):
        if None == JBoxUserV2.TABLE:
            return None
        if JBoxUserV2.TABLE is None:
            return (None, None)
        return (self.item.get('image', None), self.item.get('resource_profile', JBoxUserV2.RESOURCE_PROFILE_BASIC))
    
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
