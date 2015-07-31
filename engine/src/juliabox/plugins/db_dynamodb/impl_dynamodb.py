__author__ = 'tan'

from boto.dynamodb2.exceptions import ItemNotFound
from boto.dynamodb2.table import Table

from juliabox.db import JBoxDBPlugin, JBoxDBItemNotFound


class JBoxDynamoDB(JBoxDBPlugin):
    provides = [JBoxDBPlugin.PLUGIN_DB, JBoxDBPlugin.PLUGIN_DB_DYNAMODB]

    @staticmethod
    def configure():
        pass

    @staticmethod
    def table_open(tablename):
        return Table(tablename)

    @staticmethod
    def record_create(table, data):
        if not table.put_item(data=data):
            raise Exception("Error creating record")

    @staticmethod
    def record_fetch(table, **kwargs):
        try:
            return table.get_item(**kwargs)
        except ItemNotFound:
            raise JBoxDBItemNotFound()

    @staticmethod
    def record_scan(table, **kwargs):
        return table.scan(**kwargs)

    @staticmethod
    def record_query(table, **kwargs):
        return table.query_2(**kwargs)

    @staticmethod
    def record_count(table, **kwargs):
        return table.query_count(**kwargs)

    @staticmethod
    def record_save(table, record):
        if table is not None:
            record.save()

    @staticmethod
    def record_delete(table, record):
        if table is not None:
            record.delete()