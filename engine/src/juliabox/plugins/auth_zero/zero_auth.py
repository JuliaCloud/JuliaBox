__author__ = 'tan'
import os

import tornado
import tornado.web
import tornado.gen
import tornado.httpclient

from juliabox.jbox_util import unquote
from juliabox.handlers import JBPluginHandler, JBPluginUI


class ZeroAuthUIHandler(JBPluginUI):
    provides = [JBPluginUI.JBP_UI_AUTH_BTN]
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def get_template(plugin_type):
        if plugin_type == JBPluginUI.JBP_UI_AUTH_BTN:
            return os.path.join(ZeroAuthUIHandler.TEMPLATE_PATH, "zero_login_btn.tpl")


class ZeroAuthHandler(JBPluginHandler):
    """
    Zero authentication login. For use in a personal or development setup.
    This is included, but not enabled in JuliaBox engine by default.
    Accepts an email id for identification only, so it is possible to have multiple users, each with
    their own storage and sessions.
    """
    provides = [JBPluginHandler.JBP_HANDLER,
                JBPluginHandler.JBP_HANDLER_AUTH,
                JBPluginHandler.JBP_HANDLER_AUTH_ZERO]

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxauth/zero/", ZeroAuthHandler)])

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        user_id = unquote(self.get_argument("user_id"))
        self.post_auth_launch_container(user_id)