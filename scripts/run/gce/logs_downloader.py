#!/usr/bin/python

import os
from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
from datetime import datetime

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                             "engine", "src"))
from juliabox.jbox_util import retry_on_errors

conf = None
with open('/jboxengine/conf/jbox.user') as f:
    conf = eval(f.read())
ch = conf.get('cloud_host')
if not ch:
    print('Error: `cloud_host` entry not found in jbox.user')
    exit(-1)
INSTALL_ID = ch['install_id']

creds = GoogleCredentials.get_application_default()
conn = build('logging', 'v2beta1', credentials=creds).entries()

RFC_3339_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

@retry_on_errors()
def _list_logs(body):
    return conn.list(body=body).execute()

def list_logs(tsstart, tsend):
    fil = """
resource.type="gce_instance" AND
timestamp>="%s" AND
timestamp<="%s"
""" % (tstart, tend)

    body = {
        'projectIds': [
            INSTALL_ID,
        ],
        'filter': fil,
    }

    l = _list_logs(body)
    next_page_token = l.get('nextPageToken', None)
    entries = l.get('entries')
    if not entries:
        return []
    print("Got %d entries" % len(entries))

    while next_page_token:
        body['pageToken'] = next_page_token
        l = _list_logs(body)
        next_page_token = l.get('nextPageToken', None)
        entries.extend(l['entries'])
        print("Got %d entries" % len(entries))

    return entries

def has_key_multi(d, keys):
    if not isinstance(keys, list):
        raise Exception('keys needs to be a list')
    l = len(keys)
    for i in range(l):
        key = keys[i]
        if not d.has_key(key):
            return False
        d = d[key]
        if not isinstance(d, dict):
            if i == l - 1:
                return True
            else:
                return False
    return True

def get_logs_dict(entries):
    logs = dict()
    for e in entries:
        if not has_key_multi(e, ['textPayload']) or \
           not has_key_multi(e, ['resource', 'labels', 'instance_id']) or \
           not has_key_multi(e, ['labels', 'source']):
            continue

        log_text = e['textPayload']
        instance = e['resource']['labels']['instance_id']
        if not logs.has_key(instance):
            logs[instance] = dict()
        source = e['labels']['source']
        if not logs[instance].has_key(source):
            logs[instance][source] = [log_text]
        else:
            logs[instance][source].append(log_text)
    return logs

def write_logs(logs_dict, path):
    for instance, v in logs_dict.iteritems():
        folder = os.path.join(path, instance)
        if not os.path.isdir(folder):
            os.mkdir(folder)
        for f, logs in v.iteritems():
            with open(os.path.join(folder, f), 'w') as f:
                f.write('\n'.join(logs))

INPUT_DT_FORMAT = '%d/%m/%Y %H:%M:%S'
def convert_dt(dt):
    return datetime.strptime(dt, INPUT_DT_FORMAT).strftime(RFC_3339_FORMAT)

if __name__ == '__main__':
    tstart = raw_input('Enter start datetime (DD/MM/YYYY HH:MM:SS): ')
    tstart = convert_dt(tstart)
    tend = raw_input('Enter end datetime (DD/MM/YYYY HH:MM:SS): ')
    tend = convert_dt(tend)
    path = raw_input('Enter the download directory: ')
    with open(os.path.join(path, 'meta.txt'), 'w') as f:
        f.write('Project: %r\nStart datetime: %r\nEnd datetime: %r' % 
                (INSTALL_ID, tstart, tend))
    entries = list_logs(tstart, tend)
    if len(entries) == 0:
        print 'No logs during this interval.'
        exit(0)
    logs = get_logs_dict(entries)
    write_logs(logs, path)
