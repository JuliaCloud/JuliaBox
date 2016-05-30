__author__ = 'Nishanth'


from juliabox.cloud import JBPluginCloud
from juliabox.jbox_util import JBoxCfg, retry_on_errors
from googleapiclient.discovery import build
from oauth2client.client import GoogleCredentials
import threading

class JBoxGCD(JBPluginCloud):
    provides = [JBPluginCloud.JBP_DNS, JBPluginCloud.JBP_DNS_GCD]
    threadlocal = threading.local()
    INSTALLID = None
    REGION = None
    DOMAIN = None

    @staticmethod
    def configure():
        cloud_host = JBoxCfg.get('cloud_host')
        JBoxGCD.INSTALLID = cloud_host['install_id']
        JBoxGCD.REGION = cloud_host['region']
        JBoxGCD.DOMAIN = cloud_host['domain']

    @staticmethod
    def domain():
        if JBoxGCD.DOMAIN is None:
            JBoxGCD.configure()
        return JBoxGCD.DOMAIN

    @staticmethod
    def connect():
        c = getattr(JBoxGCD.threadlocal, 'conn', None)
        if c is None:
            JBoxGCD.configure()
            creds = GoogleCredentials.get_application_default()
            JBoxGCD.threadlocal.conn = c = build("dns", "v1", credentials=creds)
        return c

    @staticmethod
    @retry_on_errors(retries=2)
    def add_cname(name, value):
        JBoxGCD.connect().changes().create(
            project=JBoxGCD.INSTALLID, managedZone=JBoxGCD.REGION,
            body={'kind': 'dns#change',
                  'additions': [
                      {'rrdatas': [value],
                       'kind': 'dns#resourceRecordSet',
                       'type': 'A',
                       'name': name,
                       'ttl': 300}    ] }).execute()

    @staticmethod
    @retry_on_errors(retries=2)
    def delete_cname(name):
        resp = JBoxGCD.connect().resourceRecordSets().list(
            project=JBoxGCD.INSTALLID, managedZone=JBoxGCD.REGION,
            name=name, type='A').execute()
        if len(resp['rrsets']) == 0:
            JBoxGCD.log_debug('No prior dns registration found for %s', name)
        else:
            cname = resp['rrsets'][0]['rrdatas'][0]
            ttl = resp['rrsets'][0]['ttl']
            JBoxGCD.connect().changes().create(
                project=JBoxGCD.INSTALLID, managedZone=JBoxGCD.REGION,
                body={'kind': 'dns#change',
                      'deletions': [
                          {'rrdatas': [str(cname)],
                           'kind': 'dns#resourceRecordSet',
                           'type': 'A',
                           'name': name,
                           'ttl': ttl}    ] }).execute()
            JBoxGCD.log_warn('Prior dns registration was found for %s', name)
