import boto.dynamodb.exceptions
import datetime
import pytz
from jbox_crypto import encrypt, decrypt

from db.db_base import JBoxDB


class JBoxUser(JBoxDB):
    NAME = 'jbox_users'
    TABLE = None

    def __init__(self, user_id, create=False, verified=0):
        if self.table() is None:
            self.item = None
            self.is_new = False
            return
        
        try:
            self.item = self.table().get_item(user_id)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError:
            if create:
                self.item = self.table().new_item(hash_key=user_id)
                self.item['time_created'] = datetime.datetime.now(pytz.utc).isoformat()
                self.item['verified'] = verified
                self.is_new = True
            else:
                raise
    
    def save(self):
        if self.item is not None:
            self.item['time_updated'] = datetime.datetime.now(pytz.utc).isoformat()
        super(JBoxUser, self).save()

    def set_gtok(self, gtok):
        if self.item is not None:
            self.item['gtok'] = encrypt(gtok, self.enckey())

    def set_verified(self, verified=1):
        if self.item is not None:
            self.item['verified'] = verified

    def get_verified(self):
        if self.item is not None:
            return self.item.get('verified', 0)
        else:
            return 0

    def set_invite_code(self, invite_code):
        if self.item is not None:
            self.item['invitecode'] = invite_code
    
    def get_invite_code(self):
        if self.item is not None:
            return self.item.get('invitecode', None)
        else:
            return None

    def get_gtok(self):
        if self.item is not None:
            gtok = self.item.get('gtok', None)
            return decrypt(gtok, self.enckey()) if (gtok is not None) else None
        else:
            return None