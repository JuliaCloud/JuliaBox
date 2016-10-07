__author__ = 'Nishanth'

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import time

from juliabox.cloud import JBPluginCloud
from juliabox.db import JBPluginDB
from juliabox.jbox_util import JBoxCfg

class JBoxSMTP(JBPluginCloud):
    provides = [JBPluginCloud.JBP_SENDMAIL, JBPluginCloud.JBP_SENDMAIL_SMTP]

    MAX_24HRS = None
    MAX_RATE_PER_SEC = None
    SENDER_PASSWORD = None
    SMTP_URL = None
    SMTP_PORT_NO = None
    CONN = None
    SENDER = None

    @staticmethod
    def configure():
        mail_data = JBoxCfg.get('user_activation')
        JBoxSMTP.SENDER = mail_data['sender']
        JBoxSMTP.SENDER_PASSWORD = mail_data.get('sender_password', "")
        JBoxSMTP.SMTP_URL = mail_data['smtp_url']
        JBoxSMTP.SMTP_PORT_NO = mail_data['smtp_port_no']
        JBoxSMTP.MAX_24HRS = mail_data['max_24hrs']
        JBoxSMTP.MAX_RATE_PER_SEC = mail_data['max_rate_per_sec']

    @staticmethod
    def connect():
        if not JBoxSMTP.CONN:
            JBoxSMTP.configure()
            JBoxSMTP.CONN = smtplib.SMTP(JBoxSMTP.SMTP_URL, JBoxSMTP.SMTP_PORT_NO)
            try:
                JBoxSMTP.CONN.starttls()
                JBoxSMTP.CONN.login(JBoxSMTP.SENDER, JBoxSMTP.SENDER_PASSWORD)
            except smtplib.SMTPException:
                JBoxSMTP.log_info("Server does not support TLS, proceeding without authentication")

        return JBoxSMTP.CONN

    DB_PLUGIN = None
    @staticmethod
    def _get_db_plugin():
        if not JBoxSMTP.DB_PLUGIN:
            JBoxSMTP.DB_PLUGIN = JBPluginDB.jbox_get_plugin(JBPluginDB.JBP_DB_CLOUDSQL)
        return JBoxSMTP.DB_PLUGIN

    @staticmethod
    def _make_mail_entry(rcpt, sender):
        plugin = JBoxSMTP._get_db_plugin()
        if plugin == None:
            JBoxSMTP.log_warn("No mail DB, not logging mail sent")
            return
        conn = plugin.conn()
        c = conn.cursor()

        now = int(time.time())
        c.execute('INSERT INTO mails (rcpt, sender, timestamp) values ' \
                  '("%s", "%s", %d)' % (rcpt, sender, now))
        conn.commit()
        c.close()

    @staticmethod
    def _get_num_emails_in_last_24hrs():
        plugin = JBoxSMTP._get_db_plugin()
        conn = plugin.conn()
        c = conn.cursor()

        last24 = int(time.time()) - 24*60*60
        c.execute('SELECT COUNT(*) FROM mails WHERE timestamp > %d' % last24)
        ret = c.fetchone()[0]
        c.close()
        return ret

    @staticmethod
    def get_email_rates():
        JBoxSMTP.connect()
        max_24_hrs = JBoxSMTP.MAX_24HRS
        used_24_hrs = JBoxSMTP._get_num_emails_in_last_24hrs()
        max_rate_per_sec = JBoxSMTP.MAX_RATE_PER_SEC
        return max_24_hrs-used_24_hrs, max_rate_per_sec

    @staticmethod
    def send_email(rcpt, sender, subject, body):
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = rcpt
        msg['Subject'] = subject
        body = body
        msg.attach(MIMEText(body, 'plain'))

        text = msg.as_string()
        conn = JBoxSMTP.connect()
        try:
            conn.sendmail(sender, rcpt, text)
        except smtplib.SMTPHeloError:
            try:
                JBoxSMTP.CONN.quit()
            except:
                pass
            JBoxSMTP.CONN = None
            JBoxSMTP.connect().sendmail(sender, rcpt, text)

        JBoxSMTP._make_mail_entry(rcpt, sender)
