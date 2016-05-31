import datetime
import pytz
import json
import random

from boto.dynamodb2.fields import HashKey, RangeKey, AllIndex, IncludeIndex
from boto.dynamodb2.types import NUMBER, STRING

from juliabox.db import JBPluginDB
from juliabox.db import JBoxDB


class JBoxAccountingV2(JBPluginDB):
    provides = [JBPluginDB.JBP_TABLE_DYNAMODB, JBPluginDB.JBP_USAGE_ACCOUNTING]

    NAME = 'jbox_accounting_v2'

    SCHEMA = [
        HashKey('stop_date', data_type=NUMBER),
        RangeKey('stop_time', data_type=NUMBER)
    ]

    INDEXES = [
        AllIndex('container_id-stop_time-index', parts=[
            HashKey('container_id', data_type=STRING),
            RangeKey('stop_time', data_type=NUMBER)
        ]),
        IncludeIndex('image_id-stop_time-index', parts=[
            HashKey('image_id', data_type=STRING),
            RangeKey('stop_time', data_type=NUMBER)
        ], includes=['container_id'])
    ]

    KEYS = ['stop_date', 'stop_time']
    ATTRIBUTES = ['image_id', 'container_id', 'start_date', 'start_time']
    SQL_INDEXES = [
        {'name': 'container_id-stop_time-index',
         'cols': ['container_id', 'stop_time']},
        {'name': 'image_id-stop_time-index',
         'cols': ['image_id', 'stop_time']},
    ]
    KEYS_TYPES = [JBoxDB.INT, JBoxDB.INT]
    TYPES = [JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.INT, JBoxDB.INT]

    TABLE = None
    _stats_cache = {}

    def __init__(self, container_id, image_id, start_time, stop_time=None):
        if None == stop_time:
            stop_datetime = datetime.datetime.now(pytz.utc)
        else:
            stop_datetime = stop_time

        stop_time = JBoxAccountingV2.datetime_to_epoch_secs(stop_datetime, allow_microsecs=True)
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
        self.item = self.fetch(stop_date=stop_date, stop_time=stop_time)
        self.is_new = True

    @staticmethod
    def _query_stats_date(date):
        # TODO: caching items is not a good idea. Should cache computed data instead.
        today = datetime.datetime.now()
        date_day = JBoxAccountingV2.datetime_to_yyyymmdd(date)
        today_day = JBoxAccountingV2.datetime_to_yyyymmdd(today)
        istoday = date_day == today_day

        if date_day in JBoxAccountingV2._stats_cache:
            return JBoxAccountingV2._stats_cache[date_day]

        res = JBoxAccountingV2.query(stop_date__eq=date_day, stop_time__gte=0)

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
        container_freq = {}
        for date in dates:
            items = JBoxAccountingV2._query_stats_date(date)
            for x in items:
                item_count += 1
                if 'start_time' in x:
                    sum_time += x['stop_time'] - int(x['start_time'])
                try:
                    image_ids = json.loads(x['image_id'])
                except:
                    image_ids = []
                for image_id in image_ids:
                    if image_id.startswith("juliabox/") and (not image_id.endswith(":latest")):
                        image_count[image_id] = image_count.get(image_id, 0) + 1
                cid = x['container_id']
                container_freq[cid] = container_freq.get(cid, 0) + 1

        def fmt(seconds):
            hrs = int(seconds / 3600)
            mins = int(seconds / 60)
            secs = int(seconds)

            return "%dh %dm %ds" % (hrs, mins % 60, secs % 60)

        active_users = 0
        for container in container_freq:
            if container_freq[container] > 2:
                active_users += 1

        return dict(
            session_count=item_count,
            avg_time=fmt(float(sum_time) / item_count) if item_count != 0 else 'NA',
            images_used=image_count,
            unique_users=len(container_freq),
            active_users=active_users)

    @staticmethod
    def record_session_time(container_name, images_used, time_created, time_finished):
        for retry in range(1, 10):
            try:
                start_time = time_created
                finish_time = time_finished
                if retry > 1:
                    finish_time += datetime.timedelta(microseconds=random.randint(1, 100))
                acct = JBoxAccountingV2(container_name, json.dumps(images_used),
                                        start_time, stop_time=finish_time)
                acct.save()
                break
            except:
                if retry == 10:
                    JBoxAccountingV2.log_exception("error recording usage")
                else:
                    JBoxAccountingV2.log_warn("error recording usage, shall retry.")
