__author__ = 'tan'

import boto
import boto.ses

from juliabox.cloud import JBPluginCloud
from juliabox.jbox_util import JBoxCfg


class JBoxSES(JBPluginCloud):
    provides = [JBPluginCloud.JBP_SENDMAIL, JBPluginCloud.JBP_SENDMAIL_SES]

    REGION = None
    CONN = None

    @staticmethod
    def configure():
        cloud_host = JBoxCfg.get("cloud_host")
        JBoxSES.REGION = cloud_host["region"]

    @staticmethod
    def connect():
        if JBoxSES.CONN is None:
            JBoxSES.configure()
            JBoxSES.CONN = boto.ses.connect_to_region(JBoxSES.REGION)
        return JBoxSES.CONN

    @staticmethod
    def get_email_rates():
        resp = JBoxSES.connect().get_send_quota()
        quota = resp['GetSendQuotaResponse']['GetSendQuotaResult']
        max_24_hrs = int(float(quota['Max24HourSend']))
        used_24_hrs = int(float(quota['SentLast24Hours']))
        max_rate_per_sec = int(float(quota['MaxSendRate']))
        return max_24_hrs-used_24_hrs, max_rate_per_sec

    @staticmethod
    def send_email(rcpt, sender, subject, body):
        JBoxSES.connect().send_email(source=sender, subject=subject, body=body, to_addresses=[rcpt])
