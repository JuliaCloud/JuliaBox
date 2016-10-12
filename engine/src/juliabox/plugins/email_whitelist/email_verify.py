import os
from juliabox.jbox_util import unquote, JBoxCfg
from juliabox.handlers import JBPluginHandler
from juliabox.db import JBoxUserV2, JBoxDBItemNotFound
from email_verify_tbl import EmailVerifyDB
from impl_email_whitelist import EmailWhitelistHandler
import urllib
from juliabox.cloud import JBPluginCloud

__author__ = 'barche'


class EmailVerifyHandler(JBPluginHandler):
    provides = [JBPluginHandler.JBP_HANDLER]

    CONFIGURED = False
    EMAIL_PLUGIN = None
    EMAIL_SENDER = ""

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxauth/email_verify/", EmailVerifyHandler)])

    @staticmethod
    def configure():
        if not EmailVerifyHandler.CONFIGURED:
            plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_SENDMAIL)
            if plugin is None:
                EmailVerifyHandler.log_error("No plugin found for sending mails. Cannot send verification mail.")
            EmailVerifyHandler.EMAIL_PLUGIN = plugin
            EmailVerifyHandler.EMAIL_SENDER = JBoxCfg.get('user_activation')['sender']

            EmailVerifyHandler.CONFIGURED = True



    def get(self):
        EmailVerifyHandler.configure()

        email = unquote(self.get_argument("email", None))
        user_id = unquote(self.get_argument("user_id", None))
        verification_code = unquote(self.get_argument("verification_code", None))
        if user_id == None or email == None:
            EmailVerifyHandler.log_error("Bad request to email handler")
            return

        EmailVerifyHandler.log_info("Request to verify email %s with user_id %s", email, user_id)

        if not EmailWhitelistHandler.is_whitelisted(email):
            self.render(os.path.join(EmailWhitelistHandler.TEMPLATE_PATH, "email_whitelist.tpl"), cfg=JBoxCfg.nv, user_id=user_id, message="ERROR: entered email is not whitelisted, please try again:")
            return

        if verification_code == None:
            record = EmailVerifyDB(user_id)
            record.set_email(email)

            base_uri = self.request.protocol + "://" + self.request.host + self.request.uri.split('?')[0]
            mail_body = base_uri + '?' + urllib.urlencode({
                "user_id": user_id,
                "email": email,
                "verification_code": record.get_code()
            })
            EmailVerifyHandler.EMAIL_PLUGIN.send_email(email, EmailVerifyHandler.EMAIL_SENDER, 'JuliaBox account activation', mail_body)

            self.render(os.path.join(EmailWhitelistHandler.TEMPLATE_PATH, "message.tpl"), cfg=JBoxCfg.nv, message="Email sent. Please click the link in the mail.")
        else:
            record = EmailVerifyDB(user_id)
            if record.verify(verification_code):
                s = dict(error="", success="Verification OK, please log in again", info="", pending_activation=False, user_id="")
                self.rendertpl("index.tpl", cfg=JBoxCfg.nv, state=s)
            else:
                self.render(os.path.join(EmailWhitelistHandler.TEMPLATE_PATH, "message.tpl"), cfg=JBoxCfg.nv, message="Verification failed.")
