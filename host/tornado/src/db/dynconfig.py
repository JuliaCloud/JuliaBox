import json
import datetime
import isodate
import pytz

import boto.dynamodb2.exceptions

from db.db_base import JBoxDB
from jbox_util import parse_iso_time


class JBoxDynConfig(JBoxDB):
    NAME = 'jbox_dynconfig'
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