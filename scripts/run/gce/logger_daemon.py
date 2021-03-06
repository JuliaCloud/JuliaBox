#!/usr/bin/python

# Add the following to jbox.user
# 'cloud_host' : {
#     ...,
#     'log-interval': 5, # seconds
# }


from time import sleep, time
import os
from os import stat
from sys import argv
import httplib
from socket import gethostname
from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import errno
import json
import requests
import subprocess

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                             "engine", "src"))
from juliabox.jbox_util import retry_on_errors

if len(argv) < 2:
    print('USAGE: ./logger_daemon.py <log_files_paths>')
    exit(-1)

conf = None
with open('/jboxengine/conf/jbox.user') as f:
    conf = eval(f.read())
LOGPATHS = argv[1:]

ch = conf.get('cloud_host')
if not ch:
    print('Error: `cloud_host` entry not found in jbox.user')
    exit(-1)

INTERVAL = ch.get('log-interval', 5)
INSTALL_ID = ch['install_id']

creds = GoogleCredentials.get_application_default()
conn = build('logging', 'v2beta1', credentials=creds)
MYNAME = gethostname()
logurl = 'projects/%s/logs/%s' % (ch['install_id'], MYNAME)

p = subprocess.Popen(['uname', '-n'], stdout=subprocess.PIPE)
INSTANCE_ID = p.communicate()[0].strip()
ZONE = json.loads(requests.get(
    "http://metadata.google.internal/computeMetadata/v1/instance/?recursive=true",
    headers={"Metadata-Flavor": "Google"}).text)["zone"].split('/')[-1]

@retry_on_errors()
def cloud_log(data_list):
    ent = conn.entries()
    body = {
        'entries': data_list,
    }
    try:
        ent.write(body=body).execute()
    except HttpError, e:
        if e.resp.status != 400:
            raise

def get_log_data(line, source, sev=None):
    if not sev:
        try:
            sev = line.split(' - ')[1]
            if sev not in ['INFO', 'DEBUG', 'WARNING', 'CRITICAL', 'ERROR']:
                sev = 'INFO'
        except:
            sev = 'INFO'

    data = {
        'severity': sev,
        'textPayload': line,
        'logName': logurl,
        'resource': {
            'labels': {
                'instance_id': INSTANCE_ID,
                'zone': ZONE,
            },
            'type': 'gce_instance'
        },
        'labels': {
            'source': source,
        },
    }
    return data

class FileData:
    def __init__(self, file_name, path):
        self.file_name = file_name
        self.full_path = os.path.join(path, file_name)
        self.inode_number = stat(self.full_path).st_ino
        self.file_handle = None

        parts = self.file_name.split('.')
        try:
            self.version_number = int(parts[-1])
        except ValueError:
            self.version_number = 0

        self.is_error_file = '_err.log' in self.file_name

        if self.version_number == 0:
            self.prefix_name = self.file_name
        else:
            self.prefix_name = '.'.join(parts[:-1])

        self.deprecated = False

    def open(self):
        self.file_handle = open(self.full_path)

    def upload_lines(self):
        flag = 'ERROR' if self.is_error_file else None
        data_list = []
        for line in self.file_handle.read().split('\n'):
            if line:
                data_list.append(get_log_data(line, self.file_name, flag))
        cloud_log(data_list)

def get_file_data(path):
    return [FileData(f, path) for f in os.listdir(path)]

def filter_old_versions(ls):
    for f in ls:
        if f.deprecated:
            continue
        for g in ls:
            if g.deprecated:
                continue
            if f.inode_number != g.inode_number and f.prefix_name == g.prefix_name:
                if g.version_number > f.version_number:
                    f.deprecated = True
                    break
                else:
                    g.deprecated = True

    return filter(lambda x: not x.deprecated, ls)

def update_fd_list(ls):
    newls = []
    for l in LOGPATHS:
        newls.extend(filter_old_versions(get_file_data(l)))

    # There are 3 kinds of files:
    # Old :- Files to which logs will no longer be written to.
    # Current :- Files to which logs are being written and handle
    #            has been opened in previous iterations.
    # New :- Files to which logs are being written and handle
    #        has not yet been opened.

    # Close old files
    for fd in ls:
        is_old = True
        for nfd in newls:
            if fd.inode_number == nfd.inode_number:
                is_old = False
                break
        if is_old:
            fd.file_handle.close()

    resultls = []
    # Open new files
    for nfd in newls:
        is_new = True
        for fd in ls:
            if fd.inode_number == nfd.inode_number:
                resultls.append(fd)
                is_new = False
                break
        if is_new:
            nfd.open()
            resultls.append(nfd)

    return resultls

def log():
    fd_list = []
    while True:
        start = time()
        fd_list = update_fd_list(fd_list)
        for f in fd_list:
            f.upload_lines()
        sleep_time = INTERVAL - (time() - start)
        if sleep_time < 0:
            sleep_time = 0
        sleep(sleep_time)

if __name__ == '__main__':
    log()
