import os
from juliabox.jbox_util import JBoxCfg
from juliabox.handlers import JBPluginHandler
from juliabox.db import JBoxUserV2, JBoxDBItemNotFound

__author__ = 'tan'


class SiteRedirectHandler(JBPluginHandler):
    provides = [JBPluginHandler.JBP_HANDLER_POST_AUTH]

    TYPE_ALL = 1
    TYPE_NEW = 2
    REDIRECT_URL = None
    REDIRECT_MSG = None
    REDIRECT_TYPE = TYPE_NEW
    CONFIGURED = False
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def configure():
        if not SiteRedirectHandler.CONFIGURED:
            data = JBoxCfg.get('site_redirect')
            SiteRedirectHandler.REDIRECT_URL = data['url']
            SiteRedirectHandler.REDIRECT_MSG = data['msg']
            rtype = data.get('user_type', 'new')
            SiteRedirectHandler.REDIRECT_TYPE = SiteRedirectHandler.TYPE_ALL if rtype == 'all' \
                else SiteRedirectHandler.TYPE_NEW

            SiteRedirectHandler.log_info("Configured to redirect %s users to %s",
                                         rtype, SiteRedirectHandler.REDIRECT_URL)
            SiteRedirectHandler.CONFIGURED = True

    @staticmethod
    def process_user_id(handler, user_id):
        SiteRedirectHandler.configure()

        redirect = True
        if SiteRedirectHandler.REDIRECT_TYPE == SiteRedirectHandler.TYPE_NEW:
            try:
                # check if user id is already registered
                JBoxUserV2(user_id, create=False)
                redirect = False
            except JBoxDBItemNotFound:
                pass

        if redirect:
            handler.render(os.path.join(SiteRedirectHandler.TEMPLATE_PATH, "redirect.tpl"),
                           cfg=JBoxCfg.nv,
                           redirect_url=SiteRedirectHandler.REDIRECT_URL,
                           redirect_msg=SiteRedirectHandler.REDIRECT_MSG)
            SiteRedirectHandler.log_info("Redirected user %s to %s", user_id, SiteRedirectHandler.REDIRECT_URL)
            return False
        else:
            return True