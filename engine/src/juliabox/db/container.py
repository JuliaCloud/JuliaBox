import json

from boto.dynamodb2.fields import HashKey
from boto.dynamodb2.types import STRING

from juliabox.db import JBoxDB, JBoxDBItemNotFound


class JBoxSessionProps(JBoxDB):
    NAME = 'jbox_session'

    SCHEMA = [
        HashKey('session_id', data_type=STRING)
    ]

    INDEXES = None

    TABLE = None

    KEYS = ['session_id']
    ATTRIBUTES = ['user_id', 'snapshot_id', 'message']

    def __init__(self, session_id, create=False, user_id=None):
        try:
            self.item = self.fetch(session_id=session_id)
            self.is_new = False
        except JBoxDBItemNotFound:
            if create:
                data = {
                    'session_id': session_id
                }
                if user_id is not None:
                    data['user_id'] = user_id
                self.create(data)
                self.item = self.fetch(session_id=session_id)
                self.is_new = True
            else:
                raise

    def get_user_id(self):
        return self.get_attrib('user_id')

    def set_user_id(self, user_id):
        self.set_attrib('user_id', user_id)

    def get_snapshot_id(self):
        return self.get_attrib('snapshot_id')

    def set_snapshot_id(self, snapshot_id):
        self.set_attrib('snapshot_id', snapshot_id)

    def get_message(self):
        msg = self.get_attrib('message')
        if msg is not None:
            msg = json.loads(msg)
        return msg

    def set_message(self, message, delete_on_display=True):
        msg = {
            'msg': message,
            'del': delete_on_display
        }
        self.set_attrib('message', json.dumps(msg))