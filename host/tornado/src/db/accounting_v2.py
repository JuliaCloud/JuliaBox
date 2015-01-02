import datetime
import pytz
import json

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
        data = {
            'stop_date': stop_date,
            'stop_time': stop_time,
            'image_id': image_id,
            'container_id': container_id,
            'start_time': JBoxAccountingV2.datetime_to_epoch_secs(start_time),
            'start_date': JBoxAccountingV2.datetime_to_yyyymmdd(start_time)
        }
        self.create(data)
        self.item = self.table().get_item(stop_date=stop_date, stop_time=stop_time)
        self.is_new = True

    @staticmethod
    def query_stats_date(date):
        # TODO: caching items is not a good idea. Should cache computed data instead.
        if None == JBoxAccountingV2.table():
            return []

        today = datetime.datetime.now()
        date_day = JBoxAccountingV2.datetime_to_yyyymmdd(date)
        today_day = JBoxAccountingV2.datetime_to_yyyymmdd(today)
        istoday = date_day == today_day

        if date_day in JBoxAccountingV2._stats_cache:
            return JBoxAccountingV2._stats_cache[date_day]

        res = JBoxAccountingV2.table().query_2(stop_date__eq=date_day, stop_time__gte=0)

        items = []
        for item in res:
            items.append(item)

        if not istoday:
            JBoxAccountingV2._stats_cache[date_day] = items

        return items

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
                image_ids = json.loads(x['image_id'])
                for image_id in image_ids:
                    if image_id.startswith("juliabox/") and (not image_id.endswith(":latest")):
                        image_count[image_id] = image_count.get(image_id, 0) + 1

        def fmt(seconds):
            hrs = int(seconds / 3600)
            mins = int(seconds / 60)
            secs = int(seconds)

            return "%dh %dm %ds" % (hrs, mins % 60, secs % 60)

        return dict(
            session_count=item_count,
            avg_time=fmt(float(sum_time) / item_count) if item_count != 0 else 'NA',
            images_used=image_count)
