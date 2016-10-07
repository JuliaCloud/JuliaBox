from juliabox.jbox_util import gen_random_secret
from juliabox.db import JBPluginDB, JBoxDBItemNotFound

__author__ = 'barche'


class EmailVerifyDB(JBPluginDB):
    provides = [JBPluginDB.JBP_TABLE_RDBMS]

    NAME = 'jbox_email_verify'

    TABLE = None

    KEYS = ['user_id']
    ATTRIBUTES = ['email', 'verification_code', 'is_verified']
    SQL_INDEXES = None
    KEYS_TYPES = [JBPluginDB.VCHAR]
    TYPES = [JBPluginDB.VCHAR, JBPluginDB.VCHAR, JBPluginDB.INT]

    def __init__(self, user_id):
        count = self.query_count(user_id__eq=user_id)
        create = (count == 0)

        if create:
            data = {
                'user_id': user_id,
                'email': '',
                'verification_code': gen_random_secret(),
                'is_verified': 0
            }
            self.create(data)

        self.item = self.fetch(user_id=user_id)
        self.is_new = create

    def set_email(self, email):
        self.set_attrib('email', email)
        self.save()

    def verify(self, verification_code):
        if self.get_attrib('verification_code') == verification_code:
            self.set_attrib('is_verified', 1)
            self.save()
            return True
        return False

    def get_code(self):
        return self.get_attrib('verification_code')

    def is_verified(self):
        if self.get_attrib('is_verified') == 1:
            return True
        return False
