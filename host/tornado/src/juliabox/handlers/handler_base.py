import json
import base64
import traceback
import pytz
import datetime
import os

import isodate
import tornado.escape
from tornado.web import RequestHandler

from juliabox.jbox_util import LoggerMixin, unique_sessname, unquote, JBoxCfg, JBoxPluginType
from juliabox.jbox_container import JBoxContainer
from juliabox.jbox_tasks import JBoxAsyncJob
from juliabox.jbox_crypto import signstr
from juliabox.cloud.aws import CloudHost
from juliabox.db import is_proposed_cluster_leader
from juliabox.jbox_crypto import encrypt, decrypt


class JBoxCookies(RequestHandler, LoggerMixin):
    COOKIE_AUTH = 'juliabox'
    AUTH_VALID_DAYS = 30
    AUTH_VALID_SECS = (AUTH_VALID_DAYS * 24 * 60 * 60)

    COOKIE_SESSID = 'sessname'
    COOKIE_INSTANCEID = 'instance_id'
    COOKIE_PORT_SHELL = 'hostshell'
    COOKIE_PORT_UPL = 'hostupload'
    COOKIE_PORT_IPNB = 'hostipnb'
    COOKIE_LOADING = 'loading'
    COOKIE_SIGN = 'sign'

    ALL_SESSION_COOKIES = [COOKIE_SESSID, COOKIE_SIGN, COOKIE_LOADING, COOKIE_INSTANCEID,
                           COOKIE_PORT_SHELL, COOKIE_PORT_UPL, COOKIE_PORT_IPNB]

    def __init__(self, application, request, **kwargs):
        super(JBoxCookies, self).__init__(application, request, **kwargs)
        self._user_id = None
        self._session_id = None
        self._instance_id = None
        self._ports = None
        self._loading_state = None
        self._valid_user = None
        self._valid_session = None

    def set_authenticated(self, user_id):
        t = datetime.datetime.now(pytz.utc).isoformat()
        sign = signstr(user_id + t, JBoxCfg.get('sesskey'))

        jbox_cookie = {'u': user_id, 't': t, 'x': sign}
        self.set_cookie(JBoxCookies.COOKIE_AUTH, base64.b64encode(json.dumps(jbox_cookie)))

    def set_redirect_instance_id(self, instance_id):
        self._set_container_cookies({
            JBoxCookies.COOKIE_INSTANCEID: instance_id
        })

    def set_container_initialized(self, instance_id, user_id):
        self._set_container(ports={
            JBoxCookies.COOKIE_PORT_SHELL: 0,
            JBoxCookies.COOKIE_PORT_UPL: 0,
            JBoxCookies.COOKIE_PORT_IPNB: 0
        }, instance_id=instance_id, user_id=user_id)
        self.set_loading_state(1)

    def set_loading_state(self, loading=1):
        self._set_container_cookies({
            JBoxCookies.COOKIE_LOADING: loading
        })

    def set_container_running(self, ports):
        self._set_container(ports)
        self.clear_loading()

    def get_user_id(self, validate=True):
        if (self._user_id is None) or (validate and (not self._valid_user)):
            try:
                jbox_cookie = self.get_cookie(JBoxCookies.COOKIE_AUTH)
                if jbox_cookie is None:
                    return None
                jbox_cookie = json.loads(base64.b64decode(jbox_cookie))
                if validate:
                    sign = signstr(jbox_cookie['u'] + jbox_cookie['t'], JBoxCfg.get('sesskey'))
                    if sign != jbox_cookie['x']:
                        self.log_info("signature mismatch for " + jbox_cookie['u'])
                        return None

                    d = isodate.parse_datetime(jbox_cookie['t'])
                    age = (datetime.datetime.now(pytz.utc) - d).total_seconds()
                    if age > JBoxCookies.AUTH_VALID_SECS:
                        self.log_info("cookie older than allowed days: " + jbox_cookie['t'])
                        return None
                    self._valid_user = True
                self._user_id = jbox_cookie['u']
            except:
                self.log_error("exception while reading cookie")
                traceback.print_exc()
                return None
        return self._user_id

    def get_session_id(self, validate=True):
        if self._get_container(validate=validate):
            return self._session_id
        return None

    def get_instance_id(self, validate=True):
        if self._get_container(validate=validate):
            return self._instance_id
        return None

    def get_ports(self, validate=True):
        if self._get_container(validate=validate):
            return self._ports
        return None

    def get_loading_state(self):
        return self.get_cookie(JBoxCookies.COOKIE_LOADING)

    def is_valid_user(self):
        return self.get_user_id(validate=True) is not None

    def is_valid_session(self):
        return self.get_session_id(validate=True) is not None

    def clear_container(self):
        for name in JBoxCookies.ALL_SESSION_COOKIES:
            self.clear_cookie(name)

    def clear_instance_affinity(self):
        self.clear_cookie(JBoxCookies.COOKIE_INSTANCEID)

    def clear_loading(self):
        self.clear_cookie(JBoxCookies.COOKIE_LOADING)

    def clear_authentication(self):
        self.clear_cookie(JBoxCookies.COOKIE_AUTH)

    def pack(self):
        args = dict()
        for cname in JBoxCookies.ALL_SESSION_COOKIES:
            args[cname] = self.get_cookie(cname)
        return tornado.escape.url_escape(base64.b64encode(encrypt(json.dumps(args), JBoxCfg.get('sesskey'))))

    def unpack(self, packed):
        args = json.loads(decrypt(base64.b64decode(packed), JBoxCfg.get('sesskey')))
        for cname in JBoxCookies.ALL_SESSION_COOKIES:
            cval = args[cname]
            if cval is not None:
                self.set_cookie(cname, args[cname])
            else:
                self.clear_cookie(cname)

    def _set_container_cookies(self, cookies):
        max_session_time = JBoxCfg.get('expire')
        if max_session_time == 0:
            max_session_time = JBoxCookies.AUTH_VALID_SECS
        expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=max_session_time)

        for n, v in cookies.iteritems():
            self.set_cookie(n, str(v), expires=expires)

    @staticmethod
    def _sign_cookies(cookies):
        signcomps = []
        for k in sorted(cookies):
            signcomps.append(k)
            signcomps.append(str(cookies[k]))

        #JBoxCookies.log_debug("signing cookies [%s]", '_'.join(signcomps))
        cookies[JBoxCookies.COOKIE_SIGN] = signstr('_'.join(signcomps), JBoxCfg.get('sesskey'))

    def _set_container(self, ports, instance_id=None, user_id=None):
        if instance_id is None:
            instance_id = self.get_instance_id()

        if user_id is None:
            user_id = self.get_user_id()

        cookies = {
            JBoxCookies.COOKIE_SESSID: unique_sessname(user_id),
            JBoxCookies.COOKIE_INSTANCEID: instance_id
        }
        cookies.update(ports)
        self._sign_cookies(cookies)
        #self.log_debug("setting container cookies: %r", cookies)
        self._set_container_cookies(cookies)

    def _get_container(self, validate=True):
        if (self._session_id is None) or (validate and (not self._valid_session)):
            rcvd_cookies = dict()
            for cname in [JBoxCookies.COOKIE_SESSID, JBoxCookies.COOKIE_INSTANCEID,
                          JBoxCookies.COOKIE_PORT_SHELL, JBoxCookies.COOKIE_PORT_UPL, JBoxCookies.COOKIE_PORT_IPNB]:
                rcvd_cookies[cname] = unquote(self.get_cookie(cname))

            if rcvd_cookies[JBoxCookies.COOKIE_SESSID] is None:
                return False

            if validate:
                signval = self.get_cookie(JBoxCookies.COOKIE_SIGN)
                if signval is None:
                    self.log_info('invalid session %s. signature missing', rcvd_cookies[JBoxCookies.COOKIE_SESSID])
                    return False
                signval = signval.replace('"', '')
                self._sign_cookies(rcvd_cookies)
                if rcvd_cookies[JBoxCookies.COOKIE_SIGN] != signval:
                    self.log_info('invalid session %s. signature mismatch', rcvd_cookies[JBoxCookies.COOKIE_SESSID])
                    return False
                self._valid_session = True

            self._session_id = rcvd_cookies[JBoxCookies.COOKIE_SESSID]
            self._instance_id = rcvd_cookies[JBoxCookies.COOKIE_INSTANCEID]
            self._ports = dict()
            for cname in [JBoxCookies.COOKIE_PORT_SHELL, JBoxCookies.COOKIE_PORT_UPL, JBoxCookies.COOKIE_PORT_IPNB]:
                self._ports[cname] = rcvd_cookies[cname]
        return True


class JBoxHandler(JBoxCookies):
    def __init__(self, application, request, **kwargs):
        super(JBoxHandler, self).__init__(application, request, **kwargs)

    def rendertpl(self, tpl, **kwargs):
        self.render("../../../www/" + tpl, **kwargs)

    def is_valid_req(self):
        sessname = self.get_session_id()
        if sessname is None:
            return False

        ports = self.get_ports()
        container_ports = (ports[JBoxCookies.COOKIE_PORT_SHELL],
                           ports[JBoxCookies.COOKIE_PORT_UPL],
                           ports[JBoxCookies.COOKIE_PORT_IPNB])
        if not JBoxContainer.is_valid_container("/" + sessname, container_ports):
            self.log_info('not valid req. container deleted or ports not matching')
            return False

        return True

    @classmethod
    def try_launch_container(cls, user_id, max_hop=False):
        sessname = unique_sessname(user_id)
        cont = JBoxContainer.get_by_name(sessname)
        cls.log_debug("have existing container for %s: %r", sessname, None != cont)
        if cont is not None:
            cls.log_debug("container running: %r", cont.is_running())

        if max_hop:
            self_load = CloudHost.get_instance_stats(CloudHost.instance_id(), 'Load')
            if self_load < 100:
                JBoxContainer.invalidate_container(sessname)
                JBoxAsyncJob.async_launch_by_name(sessname, user_id, True)
                return True

        is_leader = is_proposed_cluster_leader()
        if ((cont is None) or (not cont.is_running())) and (not CloudHost.should_accept_session(is_leader)):
            if cont is not None:
                JBoxContainer.invalidate_container(cont.get_name())
                JBoxAsyncJob.async_backup_and_cleanup(cont.dockid)
            return False

        JBoxContainer.invalidate_container(sessname)
        JBoxAsyncJob.async_launch_by_name(sessname, user_id, True)
        return True

    def unset_affinity(self):
        self.clear_container()
        self.set_header('Connection', 'close')
        self.request.connection.no_keep_alive = True


class JBoxUIModulePlugin(LoggerMixin):
    """ Enables providing additional sections in a JuliaBox screen.

    Features:
    - config (provides a section in the JuliaBox configuration screen)

    Methods expected:
    - get_template: return template_file to include
    """

    __metaclass__ = JBoxPluginType

    PLUGIN_CONFIG = 'config'

    @staticmethod
    def create_include_file():
        incl_file_path = os.path.join(os.path.dirname(__file__), "../../../www/admin_modules.tpl")
        with open(incl_file_path, 'w') as incl_file:
            for plugin in JBoxUIModulePlugin.plugins:
                JBoxUIModulePlugin.log_info("Found plugin %r provides %r", plugin, plugin.provides)
                template_file = plugin.get_template()

                incl_file.write('{%% module Template("%s") %%}\n' % (template_file,))


class JBoxHandlerPlugin(JBoxHandler):
    """ The base class for request handler plugins.

    It is a plugin mount point, looking for features:
    - handler (handles requests to a URL spec)
    - js (provides javascript file to be included at top level)

    Methods expected in the plugin:
    - get_uri: Provide URI handled
    - get_js: Provide javascript path to be included at top level if any
    - should also provide methods required from a tornado request handler
    """

    __metaclass__ = JBoxPluginType

    PLUGIN_HANDLER = 'handler'
    PLUGIN_JS = 'js'

    PLUGIN_JAVASCRIPTS = []

    @staticmethod
    def add_plugin_handlers(l):
        for plugin in JBoxHandlerPlugin.jbox_get_plugins(JBoxHandlerPlugin.PLUGIN_HANDLER):
            JBoxHandlerPlugin.log_info("Found plugin %r provides %r", plugin, plugin.provides)
            l.append((plugin.get_uri(), plugin))

        for plugin in JBoxHandlerPlugin.jbox_get_plugins(JBoxHandlerPlugin.PLUGIN_JS):
            JBoxHandlerPlugin.log_info("Found plugin %r provides %r", plugin, plugin.provides)
            JBoxHandlerPlugin.PLUGIN_JAVASCRIPTS.append(plugin.get_js())
