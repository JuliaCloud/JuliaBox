import json
import datetime
import pytz

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
    ATTRIBUTES = ['user_id', 'snapshot_id', 'message', 'instance_id', 'attach_time', 'container_state']
    SQL_INDEXES = None
    KEYS_TYPES = [JBoxDB.VCHAR]
    TYPES = [JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.INT, JBoxDB.VCHAR]

    # maintenance runs are once in 5 minutes
    # TODO: make configurable
    SESS_UPDATE_INTERVAL = (5 * 1.5) * 60

    def __init__(self, cluster, session_id, create=False, user_id=None):
        if session_id.startswith("/"):
            session_id = session_id[1:]
        qsession_id = JBoxDB.qual(cluster, session_id)
        try:
            self.item = self.fetch(session_id=qsession_id)
            self.is_new = False
        except JBoxDBItemNotFound:
            if create:
                data = {
                    'session_id': qsession_id
                }
                if user_id is not None:
                    data['user_id'] = user_id
                self.create(data)
                self.item = self.fetch(session_id=qsession_id)
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

    def get_instance_id(self):
        now = datetime.datetime.now(pytz.utc)
        attach_time = JBoxSessionProps.epoch_secs_to_datetime(int(self.get_attrib('attach_time', 0)))
        if (now - attach_time).total_seconds() > JBoxSessionProps.SESS_UPDATE_INTERVAL:
            return None
        return self.get_attrib('instance_id')

    def set_instance_id(self, instance_id):
        self.set_attrib('instance_id', instance_id)
        attach_time = datetime.datetime.now(pytz.utc)
        self.set_attrib('attach_time', JBoxSessionProps.datetime_to_epoch_secs(attach_time))

    def unset_instance_id(self, instance_id):
        if self.get_instance_id() == instance_id:
            self.set_instance_id("")

    def set_container_state(self, container_state):
        self.set_attrib('container_state', container_state)

    def get_container_state(self):
        self.get_attrib('container_state', '')

    @staticmethod
    def attach_instance(cluster, session_id, instance_id, container_state=None):
        sessprops = JBoxSessionProps(cluster, session_id, create=True)
        sessprops.set_instance_id(instance_id)
        if container_state:
            sessprops.set_container_state(container_state)
        sessprops.save()

    @staticmethod
    def detach_instance(cluster, session_id, instance_id):
        sessprops = JBoxSessionProps(cluster, session_id, create=True)
        sessprops.unset_instance_id(instance_id)
        sessprops.set_container_state('')
        sessprops.save()

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

    @staticmethod
    def get_active_sessions(cluster):
        now = datetime.datetime.now(pytz.utc)
        nowsecs = JBoxSessionProps.datetime_to_epoch_secs(now)
        valid_time = nowsecs - JBoxSessionProps.SESS_UPDATE_INTERVAL
        result = dict()
        for record in JBoxSessionProps.scan(session_id__beginswith=cluster, attach_time__gte=valid_time,
                                            instance_id__gt=" "):
            instance_id = record.get('instance_id', None)
            if instance_id:
                sessions = result.get(instance_id, dict())
                sessions[record.get('session_id')] = record.get('container_state', 'Unknown')
                result[instance_id] = sessions
        return result
