import boto.dynamodb2.exceptions
import datetime
import pytz
from jbox_crypto import encrypt, decrypt
from boto.dynamodb.condition import BETWEEN

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

    ACTIVATION_CODE_AUTO = 'AUTO'
    
    RESOURCE_PROFILE_BASIC = 0
    RESOURCE_PROFILE_DISK_EBS_1G = 1 << 0

    def __init__(self, user_id, create=False):
        if self.table() is None:
            self.is_new = False
            self.item = None
            return
        
        try:
            self.item = self.table().get_item(user_id=user_id)
            self.is_new = False
        except boto.dynamodb2.exceptions.ItemNotFound:
            if create:
                data = {
                    'user_id': user_id
                }
                JBoxUserV2._set_time(data, "create")
                JBoxUserV2._set_activation_state(data, '-', JBoxUserV2.ACTIVATION_NONE)
                self.create(data)
                self.item = self.table().get_item(user_id=user_id)
                self.is_new = True
            else:
                raise

    def get_user_id(self):
        return self.get_attrib('user_id', None)

    def get_status(self):
        if self.item is not None:
            return self.item.get('status', JBoxUserV2.STATUS_ACTIVE)
        else:
            return None

    def get_role(self):
        return int(self.get_attrib('role', JBoxUserV2.ROLE_USER))

    def set_role(self, role):
        if self.item is not None:
            r = self.item.get('role', JBoxUserV2.ROLE_USER)
            self.item['role'] = r | role

    def has_role(self, role):
        return self.get_role() & role == role

    def set_status(self, status):
        self.set_attrib('status', status)

    def set_time(self, prefix, dt=None):
        if self.item is None:
            return
        JBoxUserV2._set_time(self.item, prefix, dt)

    @staticmethod
    def _set_time(item, prefix, dt=None):
        if None == dt:
            dt = datetime.datetime.now(pytz.utc)

        if prefix not in ["create", "update"]:
            raise(Exception("invalid prefix for setting time"))

        item[prefix + "_month"] = JBoxUserV2.datetime_to_yyyymm(dt)
        item[prefix + "_time"] = JBoxUserV2.datetime_to_epoch_secs(dt)

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
            JBoxUserV2.log_debug("setting activation state of %s to %s, %d",
                                 self.get_user_id(), activation_code, activation_status)
            JBoxUserV2._set_activation_state(self.item, activation_code, activation_status)

    @staticmethod
    def _set_activation_state(item, activation_code, activation_status):
        item['activation_code'] = activation_code
        item['activation_status'] = activation_status

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
        return self.item.get('image', None), int(self.item.get('resource_profile', JBoxUserV2.RESOURCE_PROFILE_BASIC))

    def has_resource_profile(self, mask):
        _image, resource_profile = self.get_container_type()
        if mask == 0:
            return resource_profile == 0
        return (resource_profile & mask) == mask

    @staticmethod
    def get_pending_activations(max_count):
        records = JBoxUserV2.table().query_2(activation_code__eq=JBoxUserV2.ACTIVATION_CODE_AUTO,
                                             activation_status__eq=JBoxUserV2.ACTIVATION_REQUESTED,
                                             index='activation_code-activation_status-index',
                                             limit=max_count)
        user_ids = []
        for rec in records:
            user_ids.append(rec['user_id'])
        return user_ids

    @staticmethod
    def count_pending_activations():
        count = JBoxUserV2.table().query_count(activation_code__eq='AUTO',
                                               activation_status__eq=JBoxUserV2.ACTIVATION_REQUESTED,
                                               index='activation_code-activation_status-index')
        return count

    @staticmethod
    def count_created(hours_before, tilldate=None):
        if None == tilldate:
            tilldate = datetime.datetime.now(pytz.utc)

        fromdate = tilldate - datetime.timedelta(hours=hours_before)

        till_month = JBoxUserV2.datetime_to_yyyymm(tilldate)
        till_time = JBoxUserV2.datetime_to_epoch_secs(tilldate)

        from_month = JBoxUserV2.datetime_to_yyyymm(fromdate)
        from_time = JBoxUserV2.datetime_to_epoch_secs(fromdate)

        count = 0
        mon = from_month
        while mon <= till_month:
            count += JBoxUserV2.table().query_count(create_month__eq=mon,
                                                    create_time__between=(from_time, till_time),
                                                    index='create_month-create_time-index')

            JBoxUserV2.log_debug("adding accounts created in mon %d, from %d till %d. count %d",
                                 mon, from_time, till_time, count)

            if (mon % 100) == 12:
                mon = (mon/100 + 1)*100 + 1
            else:
                mon += 1

        return count