__author__ = 'tan'
import os

from juliabox.handlers import JBPluginHandler, JBPluginUI
from juliabox.jbox_util import JBoxCfg
from juliabox.db import JBoxUserV2, JBoxDBItemNotFound


class UserAdminUIModule(JBPluginUI):
    provides = [JBPluginUI.JBP_UI_CONFIG_SECTION]
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def get_template(plugin_type):
        if plugin_type == JBPluginUI.JBP_UI_CONFIG_SECTION:
            return os.path.join(UserAdminUIModule.TEMPLATE_PATH, "user_admin.tpl")
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
        user_id = UserAdminUIModule.get_user_id(handler)
        if user_id is None:
            return False
        user = JBoxUserV2(user_id)
        sessname = handler.get_session_id()
        is_admin = sessname in JBoxCfg.get("admin_sessnames", []) or user.has_role(JBoxUserV2.ROLE_SUPER)
        return is_admin


class UserAdminHandler(JBPluginHandler):
    provides = [JBPluginHandler.JBP_HANDLER, JBPluginHandler.JBP_JS_TOP]

    @staticmethod
    def get_js():
        return "/assets/plugins/user_admin/user_admin.js"

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxplugin/user_admin/", UserAdminHandler)])

    def get(self):
        return self.post()

    def post(self):
        self.log_debug("User management handler got POST request")
        sessname = self.get_session_id()
        user_id = self.get_user_id()

        if (sessname is None) or (user_id is None):
            self.send_error()
            return

        user = JBoxUserV2(user_id)
        is_admin = sessname in JBoxCfg.get("admin_sessnames", []) or user.has_role(JBoxUserV2.ROLE_SUPER)
        self.log_info("User manager. user_id[%s] is_admin[%r]", user_id, is_admin)

        if not is_admin:
            self.send_error(status_code=403)
            return

        if self.handle_get_user(user_id, is_admin):
            return
        if self.handle_update_user(user_id, is_admin):
            return

        self.log_error("no handlers found")
        # only AJAX requests responded to
        self.send_error()

    def handle_get_user(self, user_id, is_admin):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != "fetch"):
            return False

        fetch_uid = self.get_argument('user_id', '', strip=True)
        if fetch_uid is None or len(fetch_uid) == 0:
            response = {'code': -1, 'data': 'Invalid user id!'}
            self.write(response)
            return True

        try:
            fetch_user = JBoxUserV2(fetch_uid)
        except JBoxDBItemNotFound:
            response = {'code': -1, 'data': 'No such user - %s' % (fetch_uid,)}
            self.write(response)
            return True

        courses = ','.join(fetch_user.get_courses_offered())

        resp = {
            'user_id': fetch_user.get_user_id(),
            'role': fetch_user.get_role(),
            'resprof': fetch_user.get_resource_profile(),
            'cores': fetch_user.get_max_cluster_cores(),
            'courses': courses
        }
        response = {'code': 0, 'data': resp}
        self.write(response)
        return True

    def handle_update_user(self, user_id, is_admin):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != "update"):
            return False

        fetch_uid = self.get_argument('user_id', '', strip=True)
        if fetch_uid is None or len(fetch_uid) == 0:
            response = {'code': -1, 'data': 'Invalid user id!'}
            self.write(response)
            return True

        try:
            fetch_user = JBoxUserV2(fetch_uid)
        except JBoxDBItemNotFound:
            response = {'code': -1, 'data': 'No such user - %s' % (fetch_uid,)}
            self.write(response)
            return True

        updated = False

        cores = self.get_argument('cores', None, strip=True)
        if cores is not None and len(cores) > 0:
            cores = int(cores)
            if cores != fetch_user.get_max_cluster_cores():
                fetch_user.set_max_cluster_cores(cores)
                updated = True

        courses = self.get_argument('courses', None, strip=True)
        if courses is not None and len(courses) > 0:
            courses = courses.split(',')
            if courses != fetch_user.get_courses_offered():
                fetch_user.set_courses_offered(courses)
                updated = True

        role = self.get_argument('role', None, strip=True)
        if role is not None and len(role) > 0:
            role = int(role)
            if role != fetch_user.get_role():
                fetch_user.set_attrib('role', role)
                updated = True

        resprof = self.get_argument('resprof', None, strip=True)
        if resprof is not None and len(resprof) > 0:
            resprof = int(resprof)
            if resprof != fetch_user.get_resource_profile():
                fetch_user.set_attrib('resource_profile', resprof)
                updated = True

        if updated:
            fetch_user.save()
        response = {'code': 0, 'data': ''}
        self.write(response)
        return True