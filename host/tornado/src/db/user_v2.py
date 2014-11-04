import boto.dynamodb.exceptions
import datetime
import pytz
from jbox_crypto import encrypt, decrypt

from db.db_base import JBoxDB


class JBoxUserV2(JBoxDB):
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
        - role
        - gtok
    """
    NAME = 'jbox_users_v2'
    TABLE = None

    STATUS_ACTIVE = 0
    STATUS_INACTIVE = 1
    
    ROLE_USER = 0
    ROLE_ACCESS_STATS = 1 << 0
    ROLE_MANAGE_INVITES = 1 << 1
    ROLE_MANAGE_CONTAINERS = 1 << 2

    ROLE_SUPER = (1 << 33) - 1

    ACTIVATION_NONE = 0
    ACTIVATION_GRANTED = 1
    ACTIVATION_REQUESTED = 2
    
    RESOURCE_PROFILE_BASIC = 0
    RESOURCE_PROFILE_DISK_EBS_1G = 1 << 0

    def __init__(self, user_id, create=False):
        if self.table() is None:
            self.is_new = False
            self.item = None
            return
        
        try:
            self.item = self.table().get_item(hash_key=user_id)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError:
            if create:
                self.item = self.table().new_item(hash_key=user_id)
                self.set_time("create")
                self.set_activation_state('-', JBoxUserV2.ACTIVATION_NONE)
                self.is_new = True
            else:
                raise

    def get_user_id(self):
        if self.item is not None:
            return self.item['user_id']
        else:
            return None

    def get_status(self):
        if self.item is not None:
            return self.item.get('status', JBoxUserV2.STATUS_ACTIVE)
        else:
            return None

    def get_role(self):
        if self.item is not None:
            return self.item.get('role', JBoxUserV2.ROLE_USER)
        else:
            return JBoxUserV2.ROLE_USER

    def set_role(self, role):
        if self.item is not None:
            r = self.item.get('role', JBoxUserV2.ROLE_USER)
            self.item['role'] = r | role

    def has_role(self, role):
        return self.get_role() & role == role

    def set_status(self, status):
        if self.item is not None:
            self.item['status'] = status

    def set_time(self, prefix, dt=None):
        if self.item is None:
            return
        if None == dt:
            dt = datetime.datetime.now(pytz.utc)
    
        if prefix not in ["create", "update"]:
            raise(Exception("invalid prefix for setting time"))
        
        self.item[prefix + "_month"] = JBoxUserV2.datetime_to_yyyymm(dt)
        self.item[prefix + "_time"] = JBoxUserV2.datetime_to_epoch_secs(dt)
    
    def get_time(self, prefix):
        if self.item is None:
            return None
        if prefix not in ["create", "update"]:
            raise(Exception("invalid prefix for setting time"))
        return JBoxUserV2.epoch_secs_to_datetime(self.item[prefix + "_time"])

    def save(self, set_time=True):
        if self.item is not None:
            self.set_time("update")
        super(JBoxUserV2, self).save()

    def set_activation_state(self, activation_code, activation_status):
        if self.item is not None:
            self.item['activation_code'] = activation_code
            self.item['activation_status'] = activation_status
    
    def get_activation_state(self):
        if self.item is None:
            return None, None
        return self.item.get('activation_code', '-'), self.item.get('activation_status', JBoxUserV2.ACTIVATION_NONE)
    
    def set_gtok(self, gtok):
        if self.item is not None:
            self.item['gtok'] = encrypt(gtok, self.enckey())

    def get_gtok(self):
        if self.item is None:
            return None
        gtok = self.item.get('gtok', None)
        return decrypt(gtok, self.enckey()) if (gtok is not None) else None

    def set_container_type(self, image, resource_profile):
        if self.item is not None:
            self.item['image'] = image
            self.item['resource_profile'] = resource_profile
    
    def get_container_type(self):
        if self.item is None:
            return None, None
        return self.item.get('image', None), self.item.get('resource_profile', JBoxUserV2.RESOURCE_PROFILE_BASIC)

    def has_resource_profile(self, mask):
        _image, resource_profile = self.get_container_type()
        if mask == 0:
            return resource_profile == 0
        return (resource_profile & mask) == mask