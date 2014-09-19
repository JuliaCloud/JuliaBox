import datetime
import pytz

from boto.dynamodb.condition import GE

from db.db_base import JBoxDB


class JBoxAccountingV2(JBoxDB):
    NAME = 'jbox_accounting_v2'
    TABLE = None
    _stats_cache = {}

    def __init__(self, container_id, image_id, start_time, stop_time=None):
        if None == self.table():
            return

        if None == stop_time:
            stop_datetime = datetime.datetime.now(pytz.utc)
        else:
            stop_datetime = stop_time

        stop_time = JBoxAccountingV2.datetime_to_epoch_secs(stop_datetime)
        stop_date = JBoxAccountingV2.datetime_to_yyyymmdd(stop_datetime)
        self.item = self.table().new_item(hash_key=stop_date, range_key=stop_time)
        self.item['image_id'] = image_id
        self.item['container_id'] = container_id
        self.item['start_time'] = JBoxAccountingV2.datetime_to_epoch_secs(start_time)
        self.item['start_date'] = JBoxAccountingV2.datetime_to_yyyymmdd(start_time)
        self.is_new = True

    @staticmethod
    def query_stats_date(date):
        if None == JBoxAccountingV2.table():
            return []

        today = datetime.datetime.now()
        date_day = JBoxAccountingV2.datetime_to_yyyymmdd(date)
        today_day = JBoxAccountingV2.datetime_to_yyyymmdd(today)
        istoday = date_day == today_day

        if date_day in JBoxAccountingV2._stats_cache:
            return JBoxAccountingV2._stats_cache[date_day]

        res = JBoxAccountingV2.table().query(date_day, GE(0))

        if not istoday:
            JBoxAccountingV2._stats_cache[date_day] = res

        return res

    @staticmethod
    def get_stats(dates=(datetime.datetime.now(),)):
        sum_time = 0
        item_count = 0
        image_count = {}
        for date in dates:
            items = JBoxAccountingV2.query_stats_date(date)
            for x in items:
                item_count += 1
                if 'start_time' in x:
                    sum_time += x['stop_time'] - int(x['start_time'])
                image_count[x['image_id']] = image_count.get(x['image_id'], 0) + 1

        def fmt(seconds):
            hrs = int(seconds / 3600)
            mins = int(seconds / 60)
            secs = int(seconds)

            return "%dh %dm %ds" % (hrs, mins % 60, secs % 60)

        return dict(
            total_time=sum_time,
            session_count=item_count,
            avg_time=fmt(float(sum_time) / item_count) if item_count != 0 else 'NA',
            images_used=sorted([{'image_id': x, 'count': image_count[x]}
                                for x in image_count], key=lambda k: k['count'], reverse=True))
