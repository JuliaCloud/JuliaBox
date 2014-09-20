import datetime
import pytz

from db.db_base import JBoxDB


class JBoxAccounting(JBoxDB):
    NAME = 'jbox_accounting'
    TABLE = None

    def __init__(self, cont_id, duration_secs, image_id, time_stopped=None):
        if None == self.table():
            return

        if None == time_stopped:
            time_stopped = datetime.datetime.now(pytz.utc).isoformat()

        self.item = self.table().new_item(hash_key=cont_id, range_key=time_stopped)
        self.item['duration_secs'] = duration_secs
        self.item['image_id'] = image_id
        self.is_new = True