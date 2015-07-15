import json
import datetime
import pytz

from boto.dynamodb2.fields import HashKey
from boto.dynamodb2.types import STRING
import isodate
import boto.dynamodb2.exceptions

from juliabox.db import JBoxDB
from juliabox.jbox_util import parse_iso_time


class JBoxDynConfig(JBoxDB):
    NAME = 'jbox_dynconfig'

    SCHEMA = [
        HashKey('name', data_type=STRING)
    ]

    INDEXES = None

    TABLE = None
    DEFAULT_REGISTRATION_RATE = 60

    def __init__(self, prop, create=False, value=None):
        if self.table() is None:
            return

        self.item = None
        try:
            self.item = self.table().get_item(name=prop)
            self.is_new = False
        except boto.dynamodb2.exceptions.ItemNotFound:
            if create:
                data = {
                    'name': prop
                }
                if value is not None:
                    data['value'] = value
                self.create(data)
                self.item = self.table().get_item(name=prop)
                self.is_new = True
            else:
                raise

    @staticmethod
    def _n(cluster, name):
        return '.'.join([cluster, name])

    def set_value(self, value):
        self.set_attrib('value', value)

    def get_value(self):
        return self.get_attrib('value')

    @staticmethod
    def unset_cluster_leader(cluster):
        try:
            record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'leader'))
            record.delete()
        except boto.dynamodb2.exceptions.ItemNotFound:
            return

    @staticmethod
    def set_cluster_leader(cluster, instance):
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'leader'), create=True, value=instance)
        if not record.is_new:
            record.set_value(instance)
            record.save()

    @staticmethod
    def get_cluster_leader(cluster):
        try:
            return JBoxDynConfig(JBoxDynConfig._n(cluster, 'leader')).get_value()
        except boto.dynamodb2.exceptions.ItemNotFound:
            return None

    @staticmethod
    def set_allow_registration(cluster, allow):
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'allow_registration'), create=True, value=str(allow))
        if not record.is_new:
            record.set_value(str(allow))
            record.save()

    @staticmethod
    def get_allow_registration(cluster):
        try:
            record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'allow_registration'))
        except boto.dynamodb2.exceptions.ItemNotFound:
            return True

        return record.get_value() == 'True'

    @staticmethod
    def get_registration_hourly_rate(cluster):
        try:
            return int(JBoxDynConfig(JBoxDynConfig._n(cluster, 'registrations_hourly_rate')).get_value())
        except boto.dynamodb2.exceptions.ItemNotFound:
            return JBoxDynConfig.DEFAULT_REGISTRATION_RATE

    @staticmethod
    def set_registration_hourly_rate(cluster, rate):
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'registrations_hourly_rate'), create=True, value=str(rate))
        if not record.is_new:
            record.set_value(str(rate))
            record.save()

    @staticmethod
    def set_message(cluster, message, valid_delta):
        tnow = datetime.datetime.now(pytz.utc)
        tvalid = tnow + valid_delta

        msg = {
            'msg': message,
            'valid_till': isodate.datetime_isoformat(tvalid)
        }
        msg = json.dumps(msg)
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'message'), create=True, value=msg)
        if not record.is_new:
            record.set_value(msg)
            record.save()

    @staticmethod
    def get_message(cluster, del_expired=True):
        try:
            record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'message'))
        except boto.dynamodb2.exceptions.ItemNotFound:
            return None

        msg = record.get_value()
        if msg is None:
            return None

        msg = json.loads(msg)

        tnow = datetime.datetime.now(pytz.utc)
        tvalid = parse_iso_time(msg['valid_till'])
        #JBoxDynConfig.log_debug("tnow: %s, tvalid: %s", str(tnow), str(tvalid))
        if tvalid >= tnow:
            return msg['msg']

        if del_expired:
            JBoxDynConfig.table().delete_item(name='.'.join([cluster, 'message']))

        return None

    @staticmethod
    def get_user_home_image(cluster):
        try:
            record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'user_home_image'))
        except boto.dynamodb2.exceptions.ItemNotFound:
            return None, None, None
        img = json.loads(record.get_value())
        pkg_file = img['pkg_file'] if 'pkg_file' in img else None
        home_file = img['home_file'] if 'home_file' in img else None
        return img['bucket'], pkg_file, home_file

    @staticmethod
    def set_user_home_image(cluster, bucket, pkg_file, home_file):
        img = {
            'bucket': bucket,
            'pkg_file': pkg_file,
            'home_file': home_file
        }
        img = json.dumps(img)
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'user_home_image'), create=True, value=img)
        if not record.is_new:
            record.set_value(img)
            record.save()

    @staticmethod
    def set_stat_collected_date(cluster):
        dt = datetime.datetime.now(pytz.utc).isoformat()
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'stat_date'), create=True, value=dt)
        if not record.is_new:
            record.set_value(dt)
            record.save()

    @staticmethod
    def get_stat_collected_date(cluster):
        try:
            record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'stat_date'))
        except boto.dynamodb2.exceptions.ItemNotFound:
            return None
        return parse_iso_time(record.get_value())

    @staticmethod
    def is_stat_collected_within(cluster, days):
        last_date = JBoxDynConfig.get_stat_collected_date(cluster)
        if last_date is None:
            return False
        dt = datetime.datetime.now(pytz.utc) - datetime.timedelta(days=days)
        return last_date > dt

    @staticmethod
    def set_stat(cluster, stat_name, stat):
        val = json.dumps(stat)
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, stat_name), create=True, value=val)
        if not record.is_new:
            record.set_value(val)
            record.save()

    @staticmethod
    def get_stat(cluster, stat_name):
        try:
            record = JBoxDynConfig(JBoxDynConfig._n(cluster, stat_name))
        except boto.dynamodb2.exceptions.ItemNotFound:
            return None
        return json.loads(record.get_value())

    @staticmethod
    def get_course(cluster, course_id):
        try:
            course_key = '|'.join(['course', course_id])
            record = JBoxDynConfig(JBoxDynConfig._n(cluster, course_key))
        except boto.dynamodb2.exceptions.ItemNotFound:
            return None
        return json.loads(record.get_value())

    @staticmethod
    def set_course(cluster, course_id, course_details):
        val = json.dumps(course_details)
        course_key = '|'.join(['course', course_id])
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, course_key), create=True, value=val)
        if not record.is_new:
            record.set_value(val)
            record.save()

    @staticmethod
    def get_user_cluster_config(cluster):
        #return json.loads('{"instance_cores": 32, "instance_type": "r3.8xlarge", "key_name": "jublr", "image_id": "ami-2261794a", "instance_cost": 2.8, "sec_grps": ["juliacluster"]}')
        try:
            record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'user_cluster'))
        except boto.dynamodb2.exceptions.ItemNotFound:
            return None
        return json.loads(record.get_value())

    @staticmethod
    def set_user_cluster_config(cluster, cfg):
        val = json.dumps(cfg)
        record = JBoxDynConfig(JBoxDynConfig._n(cluster, 'user_cluster'), create=True, value=val)
        if not record.is_new:
            record.set_value(val)
            record.save()