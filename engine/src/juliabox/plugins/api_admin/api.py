__author__ = 'tan'
import os

from juliabox.handlers import JBPluginHandler, JBPluginUI
from juliabox.jbox_util import JBoxCfg
from juliabox.db import JBoxUserV2, JBoxAPISpec, JBoxDBItemNotFound


class APIAdminUIModule(JBPluginUI):
    provides = [JBPluginUI.JBP_UI_CONFIG_SECTION]
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def get_template(plugin_type):
        if plugin_type == JBPluginUI.JBP_UI_CONFIG_SECTION:
            return os.path.join(APIAdminUIModule.TEMPLATE_PATH, "api_admin.tpl")
        return None

    @staticmethod
    def get_user_id(handler):
        sessname = handler.get_session_id()
        user_id = handler.get_user_id()
        if (sessname is None) or (user_id is None):
            handler.send_error()
            return
        return user_id

    @staticmethod
    def is_allowed(handler):
        user_id = APIAdminUIModule.get_user_id(handler)
        user = JBoxUserV2(user_id)
        return user.has_resource_profile(JBoxUserV2.RES_PROF_API_PUBLISHER)


class APIAdminHandler(JBPluginHandler):
    provides = [JBPluginHandler.JBP_HANDLER, JBPluginHandler.JBP_JS_TOP]

    @staticmethod
    def get_js():
        return "/assets/plugins/api_admin/api_admin.js"

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxplugin/api_admin/", APIAdminHandler)])

    def get(self):
        return self.post()

    def post(self):
        self.log_debug("API management handler got POST request")
        sessname = self.get_session_id()
        user_id = self.get_user_id()

        if (sessname is None) or (user_id is None):
            self.send_error()
            return

        user = JBoxUserV2(user_id)
        is_admin = sessname in JBoxCfg.get("admin_sessnames", []) or user.has_role(JBoxUserV2.ROLE_SUPER)
        self.log_info("API manager. user_id[%s] is_admin[%r]", user_id, is_admin)

        if self.handle_get_api_info(user_id, is_admin):
            return
        if self.handle_create_api(user_id, is_admin):
            return
        if self.handle_delete_api(user_id, is_admin):
            return

        self.log_error("no handlers found")
        # only AJAX requests responded to
        self.send_error()

    def handle_get_api_info(self, user_id, is_admin):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != "info"):
            return False

        publisher = user_id
        api_name = None
        if is_admin:
            publisher = self.get_argument('publisher', user_id)
            api_name = self.get_argument('api_name', None)

        apiinfo = JBoxAPISpec.get_api_info(publisher, api_name)
        response = {'code': 0, 'data': apiinfo}
        self.write(response)
        return True

    def handle_delete_api(self, user_id, is_admin):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != "delete"):
            return False

        api_name = self.get_argument('api_name', None)
        if api_name is None:
            self.log_error("missing api_name")
            self.send_error()
            return True

        publisher = user_id
        if is_admin:
            publisher = self.get_argument('publisher', publisher)

        try:
            api = JBoxAPISpec(api_name=api_name)
            if api.get_publisher() != publisher:
                response = {'code': -1, 'data': 'No delete permission on this API'}
                self.write(response)
                return True
            api.delete()

            response = {'code': 0, 'data': 'API ' + api_name + ' was deleted'}
            self.write(response)
            return True
        except JBoxDBItemNotFound:
            response = {'code': 1, 'data': 'No such API - ' + api_name}
            self.write(response)
            return True

    def handle_create_api(self, user_id, is_admin):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != "create"):
            return False

        api_name = self.get_argument('api_name', '', strip=True)
        cmd = self.get_argument('cmd', '', strip=True)
        description = self.get_argument('description', '', strip=True)
        for val in (api_name, cmd, description):
            if len(val) == 0:
                self.log_error("mandatory parameters missing")
                response = {'code': -1, 'data': 'manadatory attributes missing'}
                self.write(response)
                return True
        if len(api_name) > 32 or len(cmd) > 512 or len(description) > 512:
            self.log_error("api specification fields too large")
            response = {'code': -1, 'data': 'API specification fields too large'}
            self.write(response)
            return True

        publisher = user_id
        if is_admin:
            publisher = self.get_argument('publisher', publisher, strip=True)

        try:
            JBoxAPISpec(api_name=api_name)
            response = {'code': -1, 'data': 'API already exists'}
            self.write(response)
            return True
        except JBoxDBItemNotFound:
            pass

        api = JBoxAPISpec(api_name, cmd=cmd, description=description, publisher=publisher, create=True)
        if api.get_publisher() != publisher:
            # API got created by someone else!
            response = {'code': -1, 'data': 'API already exists'}
            self.write(response)
            return True

        response = {'code': 0, 'data': ''}
        self.write(response)
        return True