import boto.dynamodb.exceptions

from db.db_base import JBoxDB


class JBoxSessionProps(JBoxDB):
    NAME = 'jbox_session'
    TABLE = None

    def __init__(self, session_id, create=False, user_id=None):
        if self.table() is None:
            return

        self.item = None
        try:
            self.item = self.table().get_item(session_id)
            self.is_new = False
        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError:
            if create:
                self.item = JBoxSessionProps.TABLE.new_item(hash_key=session_id)
                if user_id is not None:
                    self.item['user_id'] = user_id
                self.is_new = True
            else:
                raise

    def get_user_id(self):
        if self.item is not None:
            return self.item.get('user_id', None)
        else:
            return None

    def set_user_id(self, user_id):
        if self.item is not None:
            self.item['user_id'] = user_id

    def get_snapshot_id(self):
        if self.item is not None:
            return self.item.get('snapshot_id', None)
        else:
            return None

    def set_snapshot_id(self, snapshot_id):
        if self.item is not None:
            self.item['snapshot_id'] = snapshot_id