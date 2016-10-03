import os
from juliabox.jbox_util import unquote, JBoxCfg
from juliabox.handlers import JBPluginHandler
from juliabox.db import JBoxUserV2, JBoxDBItemNotFound
from email_verify_tbl import EmailVerifyDB

__author__ = 'barche'


class EmailWhitelistHandler(JBPluginHandler):
    provides = [JBPluginHandler.JBP_HANDLER,
                JBPluginHandler.JBP_HANDLER_POST_AUTH]

    WHITELIST = []
    CONFIGURED = False
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxauth/email_whitelist/", EmailWhitelistHandler)])

    def get(self):
        #EmailWhitelistHandler.log_info("State arg: %s", self.get_argument("state"))
        email = unquote(self.get_argument("email"))
        EmailWhitelistHandler.log_info("Obtained email %s", email)

    @staticmethod
    def configure():
        if not EmailWhitelistHandler.CONFIGURED:
            data = JBoxCfg.get('email_whitelist')
            if data == None:
                EmailWhitelistHandler.log_error("No email_whitelist config entry")
                return
            EmailWhitelistHandler.WHITELIST = data.get('allowed_addresses')

            if len(EmailWhitelistHandler.WHITELIST) == 0:
                EmailWhitelistHandler.log_error("No allowed_addresses config entry for email_whitelist")

            EmailWhitelistHandler.CONFIGURED = True

    @staticmethod
    def is_whitelisted(email):
        for allowed_mail in EmailWhitelistHandler.WHITELIST:
            if email.lower().endswith(allowed_mail.lower()):
                return True
        return False


    @staticmethod
    def process_user_id(handler, user_id):
        EmailWhitelistHandler.configure()

        # Check if the user_id matches
        if EmailWhitelistHandler.is_whitelisted(user_id):
            return True

        # Check if any of the users verified email addresses match
        verified_emails = EmailVerifyDB.get_verified_emails(user_id)
        for allowed_mail in EmailWhitelistHandler.WHITELIST:
            for verified_email in verified_emails:
                if EmailWhitelistHandler.is_whitelisted(verified_email):
                    return True

        # No match, create a pending email verify request
        EmailVerifyDB(user_id, "pending_email_form_response", create=True)

        handler.render(os.path.join(EmailWhitelistHandler.TEMPLATE_PATH, "email_whitelist.tpl"), cfg=JBoxCfg.nv, user_id=user_id, message="Please enter white-listed email as per tutor instructions:")

        return False
