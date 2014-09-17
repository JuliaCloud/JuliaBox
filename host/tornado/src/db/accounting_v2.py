import calendar
import datetime, pytz

from boto.dynamodb.condition import GE
from jbox_util import log_info, CloudHelper

def timestamp(date):
    return calendar.timegm(date.utctimetuple())

class JBoxAccountingV2():
    NAME = None
    SCHEMA = None
    CONN = None
    TABLE = None
    _stats_cache = {}

    def __init__(self, container_id, image_id, start_time, stop_time=None):
        if None == JBoxAccountingV2.TABLE:
            return

        if None == stop_time:
            stop_time = datetime.datetime.now(pytz.utc).isoformat()

        stop_date  = JBoxAccountingV2.make_int_date(stop_time)
        self.item = JBoxAccountingV2.TABLE.new_item(hash_key=stop_date, range_key=stop_time.isoformat())
        self.item['image_id'] = image_id
        self.item['container_id'] = container_id
        self.item['start_time'] = start_time.isoformat()
        self.item['start_date'] = JBoxAccountingV2.make_int_date(start_time)
        self.is_new = True

    @staticmethod
    def make_int_date(time):
        return int(time.strftime('%Y%m%d'))

    def save(self):
        if None == JBoxAccountingV2.TABLE:
            return
        self.item.put()
    
    def delete(self):
        if None == JBoxAccountingV2.TABLE:
            return
        self.item.delete()
    
    @staticmethod
    def _init(table_name='jbox_accounting_v2'):
        if table_name == None:
            return
        JBoxAccountingV2.NAME = table_name
        if JBoxAccountingV2.CONN == None:
            JBoxAccountingV2.CONN = CloudHelper.connect_dynamodb()
            if None != JBoxAccountingV2.CONN:
                JBoxAccountingV2.TABLE = JBoxAccountingV2.CONN.get_table(JBoxAccountingV2.NAME)
                #JBoxAccountingV2.SCHEMA = JBoxAccountingV2.CONN.create_schema(hash_key_name='stop_date', hash_key_proto_value=int, range_key_name='stop_time', range_key_proto_value=int)
                #JBoxAccountingV2.TABLE = JBoxAccountingV2.CONN.table_from_schema(name=JBoxAccountingV2.NAME, schema=JBoxAccountingV2.SCHEMA)
        log_info("JBoxAccountingV2 initialized")

    @staticmethod
    def _create_table():
        #JBoxAccountingV2.TABLE = JBoxAccountingV2.CONN.create_table(name=JBoxAccountingV2.NAME, schema=JBoxAccountingV2.SCHEMA, read_units=1, write_units=1)
        #log_info("JBoxAccountingV2 created")
        pass

    @staticmethod
    def query_stats_date(date):
        today = datetime.datetime.now()
        istoday = date.strftime('%Y%m%d') == today.strftime('%Y%m%d')
        if not istoday and date in JBoxAccountingV2._stats_cache:
            return JBoxAccountingV2._stats_cache[date]

        hash_key = JBoxAccountingV2.make_int_date(date)
        res = JBoxAccountingV2.TABLE.query(
                hash_key, GE(0))

        if not istoday:
            JBoxAccountingV2._stats_cache[date] = res
        return res

    @staticmethod
    def get_stats(dates=[datetime.datetime.now()]):
        sum_time = 0
        item_count = 0
        image_count = {}
        for date in dates:
            items = JBoxAccountingV2.query_stats_date(date)
            for x in items:
                item_count += 1
                if x.has_key('start_time'):
                    sum_time += x['stop_time'] - int(x['start_time'])
                image_count[x['image_id']] = image_count.get(x['image_id'], 0) + 1

        def fmt(seconds):
            hrs  = int(seconds / 3600)
            mins = int(seconds / 60)
            secs = int(seconds)

            return "%dh %dm %ds" % (hrs, mins % 60, secs % 60)

        return dict(
                total_time = sum_time,
                session_count = item_count,
                avg_time = fmt(float(sum_time) / item_count) if item_count != 0 else 'NA',
                images_used = sorted([{'image_id': x, 'count': image_count[x]} \
                        for x in image_count], key=lambda x: x['count'], reverse=True))

