import boto.dynamodb, boto.dynamodb.exceptions
import datetime, pytz
from jbox_util import log_info

class JBoxAccounting():
    NAME = None
    SCHEMA = None
    CONN = None
    TABLE = None
    ENCKEY = None

    def __init__(self, cont_id, duration_secs, image_id, time_stopped=None):
        if None == JBoxAccounting.TABLE:
            return
        
        if None == time_stopped:
            time_stopped = datetime.datetime.now(pytz.utc).isoformat()
        
        self.item = JBoxAccounting.TABLE.new_item(hash_key=cont_id, range_key=time_stopped)
        self.item['duration_secs'] = duration_secs
        self.item['image_id'] = image_id
        self.is_new = True
    
    def save(self):
        if None == JBoxAccounting.TABLE:
            return
        self.item.put()
    
    def delete(self):
        if None == JBoxAccounting.TABLE:
            return
        self.item.delete()
    
    @staticmethod
    def _init(table_name='jbox_accounting'):
        if table_name == None:
            return
        JBoxAccounting.NAME = table_name
        if JBoxAccounting.CONN == None:
            JBoxAccounting.CONN = boto.dynamodb.connect_to_region('us-east-1')
        if JBoxAccounting.SCHEMA == None:
            JBoxAccounting.SCHEMA = JBoxAccounting.CONN.create_schema(hash_key_name='cont_id', hash_key_proto_value=str, range_key_name='time_stopped', range_key_proto_value=str)
        if JBoxAccounting.TABLE == None:
            JBoxAccounting.TABLE = JBoxAccounting.CONN.table_from_schema(name=JBoxAccounting.NAME, schema=JBoxAccounting.SCHEMA)
            #JBoxAccounting.TABLE = JBoxAccounting.CONN.get_table(JBoxAccounting.NAME)
        log_info("JBoxAccounting initialized")

    @staticmethod
    def _create_table():
        JBoxAccounting.TABLE = JBoxAccounting.CONN.create_table(name=JBoxAccounting.NAME, schema=JBoxAccounting.SCHEMA, read_units=1, write_units=1)
        log_info("JBoxAccounting created")
        