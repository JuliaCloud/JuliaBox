from boto.dynamodb2.table import Table
from db import JBoxUserV2, JBoxInvite, JBoxDiskState, JBoxAccountingV2, JBoxDynConfig, JBoxSessionProps


def table_exists(name):
    t = Table(name)
    try:
        t.describe()
        return True
    except:
        return False

for cls in [JBoxUserV2, JBoxInvite, JBoxDiskState, JBoxAccountingV2, JBoxDynConfig, JBoxSessionProps]:
    print("Creating %s..." % (cls.NAME,))
    if table_exists(cls.NAME):
        print("\texists already!")
    else:
        Table.create(cls.NAME, schema=cls.SCHEMA, indexes=cls.INDEXES, throughput={
            'read': 1,
            'write': 1
        })
        print("\tcreated.")