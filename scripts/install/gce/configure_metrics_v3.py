#!/usr/bin/python

from sys import argv
from googleapiclient.discovery import build
from oauth2client.client import GoogleCredentials

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..',
                             'engine', 'src'))
from juliabox.jbox_util import retry_on_errors

if len(argv) != 2:
    print('Usage: ./configure_metrics <install-id>')
    exit(-1)

INSTALL_ID = argv[1]
CUSTOM_METRIC_DOMAIN = 'custom.googleapis.com/'
ALLOWED_CUSTOM_GCE_VALUE_TYPES = ['DOUBLE', 'INT64']
ALLOWED_EC2_VALUE_TYPES = ['Percent', 'Count']

def _process_value_type(value_type):
    if value_type in ALLOWED_EC2_VALUE_TYPES:
        if value_type == 'Count':
            return 'INT64'
        return 'DOUBLE'
    elif value_type in ALLOWED_CUSTOM_GCE_VALUE_TYPES:
        return value_type
    else:
        raise Exception('Invalid value_type argument.')

def _connect_google_monitoring():
    return build('monitoring', 'v3',
                 credentials=GoogleCredentials.get_application_default()).projects()

@retry_on_errors()
def _create_metric_descriptor(metric_name, value_type, label_descriptors,
                              metric_desc=''):
    value_type = _process_value_type(value_type)
    body = {
        'displayName': metric_name,
        'name': 'metricDescriptors/' + metric_name,
        'metricKind': 'GAUGE',
        'valueType': value_type,
        'labels': label_descriptors,
        'type': CUSTOM_METRIC_DOMAIN + metric_name,
        # 'unit':,
        'description': metric_desc,
    }
    md = _connect_google_monitoring().metricDescriptors()
    return md.create(name='projects/' + INSTALL_ID, body=body).execute()

def configure_metrics():
    metrics = [('NumActiveContainers', 'INT64'),
               ('NumActiveAPIContainers', 'INT64'),
               ('CPUUsed', 'DOUBLE'), ('MemUsed', 'DOUBLE'),
               ('DiskUsed', 'DOUBLE'), ('ContainersUsed', 'DOUBLE'),
               ('APIContainersUsed', 'DOUBLE'), ('DiskIdsUsed', 'DOUBLE'),
               ('Load', 'DOUBLE')]
    label_desc = [{'key': 'InstanceID',
                   'description': 'The Instance ID',
                   'valueType': 'STRING'},
                  {'key': 'GroupID',
                   'description': 'The instance group ID',
                   'valueType': 'STRING'}]
    op = []
    for (name, typ) in metrics:
        op.append(_create_metric_descriptor(name, typ, label_desc))
        print('Configured ' + name)
    return op

if __name__ == '__main__':
    print('Configuring metric descriptors...')
    configure_metrics()
    print('Done.')
