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
from juliabox.interactive import SessContainer
from juliabox.jbox_tasks import JBoxAsyncJob
from juliabox.jbox_crypto import signstr
from juliabox.cloud import Compute
from juliabox.db import is_proposed_cluster_leader, JBoxUserV2, JBoxDynConfig
from juliabox.jbox_crypto import encrypt, decrypt


class JBoxCookies(RequestHandler, LoggerMixin):
    AUTH_VALID_DAYS = 30
    AUTH_VALID_SECS = (AUTH_VALID_DAYS * 24 * 60 * 60)

    COOKIE_AUTH = 'jb_auth'
    COOKIE_SESS = 'jb_sess'
    COOKIE_INSTANCEID = 'jb_iid'
    COOKIE_LOADING = 'jb_loading'

    COOKIE_PFX_PORT = 'jp_'
    COOKIE_PORT_SHELL = 'shell'
    COOKIE_PORT_UPL = 'file'
    COOKIE_PORT_IPNB = 'nb'

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
        """ Marks user_id as authenticated with a cookie named COOKIE_AUTH (juliabox).
        Cookie contains:
        - Creation timestamp and is treated as valid for AUTH_VALID_SECS time.
        - Signature for validity check.
        :param user_id: the user id being marked as authenticated
        :return: None
        """
        t = datetime.datetime.now(pytz.utc).isoformat()
        sign = signstr(user_id + t, JBoxCfg.get('sesskey'))

        jbox_cookie = {'u': user_id, 't': t, 'x': sign}
        self.set_cookie(JBoxCookies.COOKIE_AUTH, base64.b64encode(json.dumps(jbox_cookie)))

    def set_redirect_instance_id(self, instance_id):
        """ Sets a cookie COOKIE_INSTANCEID (instance_id) to mark a destination for the router
        to redirect the next request to. This is used to implement stickyness for dedicated
        sessions. But this can also be used to route requests for load balancing.
        :param instance_id: Host to redirect to (typically an internal IP address inaccessible from public network)
        :return: None
        """
        self._set_container_cookies({
            JBoxCookies.COOKIE_INSTANCEID: instance_id
        })

    def set_container_initialized(self, instance_id, user_id):
        """ Marks a container as being allocated to a user session.
        Sets a cookie named COOKIE_SESS (jb_sess). Cookie contains:
        - Container id (session name / docker container name).
        - Container location (instance id).
        - Creation time stamp.
        - Signature for validity check.
        It also clears any stale port mapping cookies, and sets the loading state to 1.
        :param instance_id: The instance where container is allocated, to redirect future requests to.
        :param user_id: The user id for which container is allocated.
        :return: None
        """
        self.set_redirect_instance_id(instance_id)
        t = datetime.datetime.now(pytz.utc).isoformat()
        cid = unique_sessname(user_id)
        sign = signstr(cid + instance_id + t, JBoxCfg.get('sesskey'))

        sess_cookie = {'c': cid, 't': t, 'i': instance_id, 'x': sign}
        self._set_container_cookies({
            JBoxCookies.COOKIE_SESS: base64.b64encode(json.dumps(sess_cookie))
        })
        self._clear_container_ports()
        self.set_loading_state(1)

    def set_container_ports(self, ports):
        """ Sets cookies to mark the ports being accessible.
        :param ports: dict of portname and port numbers. Port name can be referred to in the URL path.
        :return:
        """
        sig1 = self._get_sig(JBoxCookies.COOKIE_AUTH)
        sig2 = self._get_sig(JBoxCookies.COOKIE_SESS)

        cookies = dict()
        for portname, portnum in ports.iteritems():
            sign = signstr(sig1 + sig2 + portname + str(portnum), JBoxCfg.get('sesskey'))
            port_cookie = {'p': portnum, 'x': sign}
            cookies[JBoxCookies.COOKIE_PFX_PORT + portname] = base64.b64encode(json.dumps(port_cookie))
        self._set_container_cookies(cookies)

    def set_loading_state(self, loading=1):
        self._set_container_cookies({
            JBoxCookies.COOKIE_LOADING: loading
        })

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
                self.log_error("exception while reading auth cookie")
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
        self.clear_cookie(JBoxCookies.COOKIE_SESS)
        self._clear_container_ports()
    #
    # def clear_instance_affinity(self):
    #     self.clear_cookie(JBoxCookies.COOKIE_INSTANCEID)
    #
    # def clear_authentication(self):
    #     self.clear_cookie(JBoxCookies.COOKIE_AUTH)

    def clear_loading(self):
        self.clear_cookie(JBoxCookies.COOKIE_LOADING)

    def pack(self):
        args = dict()
        for cookie in [JBoxCookies.COOKIE_SESS, JBoxCookies.COOKIE_INSTANCEID, JBoxCookies.COOKIE_AUTH]:
            args[cookie] = self.get_cookie(cookie)
        for cookie in self.cookies:
            if cookie.startswith(JBoxCookies.COOKIE_PFX_PORT):
                args[cookie] = self.get_cookie(cookie)
        return tornado.escape.url_escape(base64.b64encode(encrypt(json.dumps(args), JBoxCfg.get('sesskey'))))

    def unpack(self, packed):
        args = json.loads(decrypt(base64.b64decode(packed), JBoxCfg.get('sesskey')))
        for oldcookie in self.cookies:
            if oldcookie not in args or args[oldcookie] is None:
                self.clear_cookie(oldcookie)

        for cname, cval in args.iteritems():
            if cval is not None:
                self.set_cookie(cname, cval)

    def _set_container_cookies(self, cookies):
        max_session_time = JBoxCfg.get('interactive.expire')
        if max_session_time == 0:
            max_session_time = JBoxCookies.AUTH_VALID_SECS
        expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=max_session_time)

        for n, v in cookies.iteritems():
            self.set_cookie(n, str(v), expires=expires)

    def _get_container(self, validate=True):
        if (self._session_id is None) or (validate and (not self._valid_session)):
            lenpfx = len(JBoxCookies.COOKIE_PFX_PORT)
            rcvd_cookies = dict()
            for cname in [JBoxCookies.COOKIE_SESS, JBoxCookies.COOKIE_INSTANCEID]:
                rcvd_cookies[cname] = unquote(self.get_cookie(cname))

            for cookie in self.cookies:
                if cookie.startswith(JBoxCookies.COOKIE_PFX_PORT):
                    rcvd_cookies[cookie] = unquote(self.get_cookie(cookie))

            # self.log_debug("received cookies %r", rcvd_cookies)
            try:
                sess_cookie = rcvd_cookies[JBoxCookies.COOKIE_SESS]
                sess_cookie = json.loads(base64.b64decode(sess_cookie))
                # self.log_debug("received sess cookie %r", sess_cookie)
                self._session_id = sess_cookie['c']
                self._instance_id = sess_cookie['i']
                # self.log_debug("received sess_id %r, inst_id %r", self._session_id, self._instance_id)
                self._ports = dict()
                for port_cookie, port_val in rcvd_cookies.iteritems():
                    if port_cookie.startswith(JBoxCookies.COOKIE_PFX_PORT):
                        portname = port_cookie[lenpfx:]
                        port_val = base64.b64decode(port_val)
                        # self.log_debug("read port %s=%s", port_cookie, port_val)
                        port_val = json.loads(port_val)
                        if len(portname) > 0:
                            self._ports[portname] = port_val['p']
            except:
                self._valid_session = False
                self.log_error("exception while reading sess/port cookie")
                traceback.print_exc()
                return False

            if validate:
                # validate the session
                try:
                    sign = signstr(sess_cookie['c'] + sess_cookie['i'] + sess_cookie['t'], JBoxCfg.get('sesskey'))
                    if sign != sess_cookie['x']:
                        self._valid_session = False
                        self.log_info("signature mismatch for %s", sess_cookie['c'])
                        return False

                    d = isodate.parse_datetime(sess_cookie['t'])
                    age = (datetime.datetime.now(pytz.utc) - d).total_seconds()
                    if age > JBoxCookies.AUTH_VALID_SECS:
                        self.log_info("cookie for %s older than allowed days: %r", sess_cookie['c'], sess_cookie['t'])
                        return False
                    self._valid_session = True
                except:
                    self.log_error("exception while validating sess/port cookie")
                    traceback.print_exc()
                    return False

                # validate the ports
                # failure to validate a port still returns True, but removes ports from the port list
                sig1 = self._get_sig(JBoxCookies.COOKIE_AUTH)
                sig2 = sess_cookie['x']

                for port_cookie, port_val in rcvd_cookies.iteritems():
                    if port_cookie.startswith(JBoxCookies.COOKIE_PFX_PORT):
                        portname = port_cookie[lenpfx:]
                        try:
                            port_val = base64.b64decode(port_val)
                            # self.log_debug("session %s, port %s=%s", self._session_id, portname, port_val)
                            port_val = json.loads(port_val)
                            sign = signstr(sig1 + sig2 + portname + str(port_val['p']), JBoxCfg.get('sesskey'))
                            if sign != port_val['x']:
                                self.log_info('session %s port %s has signature mismatch', self._session_id, portname)
                                del self._ports[portname]
                        except:
                            self.log_error('exception parsing session %r port %r', self._session_id, portname)
                            traceback.print_exc()
                            del self._ports[portname]
        return True

    def _clear_container_ports(self):
        for cookie in self.cookies:
            if cookie.startswith(JBoxCookies.COOKIE_PFX_PORT):
                self.clear_cookie(cookie)

    def _get_sig(self, cookiename):
        cookie = self.get_cookie(cookiename)
        if cookie is None:
            raise Exception("Signature %s not found", cookiename)
        cookie = json.loads(base64.b64decode(cookie))
        return cookie['x']


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
        isvalid = True
        if not ports or \
           any(not ports.has_key(k) for k in [JBoxCookies.COOKIE_PORT_SHELL,
                                              JBoxCookies.COOKIE_PORT_UPL,
                                              JBoxCookies.COOKIE_PORT_IPNB]):
            isvalid = False
        else:
            container_ports = (ports[JBoxCookies.COOKIE_PORT_SHELL],
                               ports[JBoxCookies.COOKIE_PORT_UPL],
                               ports[JBoxCookies.COOKIE_PORT_IPNB])
            if not SessContainer.is_valid_container("/" + sessname, container_ports):
                isvalid = False

        if not isvalid:
            self.log_info('Not valid request. Container deleted or ports not matching.')
            return False

        return True

    @classmethod
    def try_launch_container(cls, user_id, max_hop=False):
        sessname = unique_sessname(user_id)
        cont = SessContainer.get_by_name(sessname)
        cls.log_debug("have existing container for %s: %r", sessname, None != cont)
        if cont is not None:
            cls.log_debug("container running: %r", cont.is_running())

        if max_hop:
            self_load = Compute.get_instance_stats(Compute.get_instance_id(), 'Load')
            if self_load < 100:
                SessContainer.invalidate_container(sessname)
                JBoxAsyncJob.async_launch_by_name(sessname, user_id, True)
                return True

        is_leader = is_proposed_cluster_leader()
        if ((cont is None) or (not cont.is_running())) and (not Compute.should_accept_session(is_leader)):
            if cont is not None:
                SessContainer.invalidate_container(cont.get_name())
                JBoxAsyncJob.async_backup_and_cleanup(cont.dockid)
            return False

        SessContainer.invalidate_container(sessname)
        JBoxAsyncJob.async_launch_by_name(sessname, user_id, True)
        return True

    def unset_affinity(self):
        self.clear_container()
        self.set_header('Connection', 'close')
        self.request.connection.no_keep_alive = True

    @staticmethod
    def is_user_activated(jbuser):
        reg_allowed = JBoxDynConfig.get_allow_registration(Compute.get_install_id())
        if jbuser.is_new:
            if not reg_allowed:
                activation_state = JBoxUserV2.ACTIVATION_REQUESTED
            else:
                activation_state = JBoxUserV2.ACTIVATION_GRANTED
            jbuser.set_activation_state(JBoxUserV2.ACTIVATION_CODE_AUTO, activation_state)
            jbuser.save()
        else:
            activation_code, activation_state = jbuser.get_activation_state()
            if reg_allowed and (activation_state != JBoxUserV2.ACTIVATION_GRANTED):
                activation_state = JBoxUserV2.ACTIVATION_GRANTED
                jbuser.set_activation_state(JBoxUserV2.ACTIVATION_CODE_AUTO, activation_state)
                jbuser.save()
            elif activation_state != JBoxUserV2.ACTIVATION_GRANTED:
                if not ((activation_state == JBoxUserV2.ACTIVATION_REQUESTED) and
                        (activation_code == JBoxUserV2.ACTIVATION_CODE_AUTO)):
                    activation_state = JBoxUserV2.ACTIVATION_REQUESTED
                    jbuser.set_activation_state(JBoxUserV2.ACTIVATION_CODE_AUTO, activation_state)
                    jbuser.save()

        return activation_state == JBoxUserV2.ACTIVATION_GRANTED

    @staticmethod
    def find_logged_in_instance(user_id):
        container_id = "/" + unique_sessname(user_id)
        instances = Compute.get_all_instances()

        for inst in instances:
            try:
                sessions = JBoxAsyncJob.sync_session_status(inst)['data']
                if len(sessions) > 0:
                    if container_id in sessions:
                        return inst
            except:
                JBoxHandler.log_error("Error receiving sessions list from %r", inst)
                pass
        return None

    def redirect_to_logged_in_instance(self, user_id):
        loggedin_instance = self.find_logged_in_instance(user_id)
        if loggedin_instance is not None \
                and loggedin_instance != Compute.get_instance_id() \
                and loggedin_instance != 'localhost':
            # redirect to the instance that has the user's session
            self.log_info("Already logged in to %s. Redirecting", loggedin_instance)
            redirect_ip = Compute.get_instance_local_ip(loggedin_instance)
            self.set_redirect_instance_id(redirect_ip)
            self.redirect('/')
            return True
        self.log_info("Logged in %s", "nowhere" if loggedin_instance is None else "here already")
        return False

    def post_auth_launch_container(self, user_id):
        for plugin in JBPluginHandler.jbox_get_plugins(JBPluginHandler.JBP_HANDLER_POST_AUTH):
            self.log_info("Passing user %r to post auth plugin %r", user_id, plugin)
            pass_allowed = plugin.process_user_id(self, user_id)
            if not pass_allowed:
                self.log_info('Login restricted for user %r by plugin %r', user_id, plugin)
                return

        jbuser = JBoxUserV2(user_id, create=True)

        if not JBPluginHandler.is_user_activated(jbuser):
            self.redirect('/?pending_activation=' + user_id)
            return

        self.set_authenticated(user_id)
        if jbuser.is_new:
            jbuser.save()

        if self.redirect_to_logged_in_instance(user_id):
            return

        # check if the current instance is appropriate for launching this
        if self.try_launch_container(user_id, max_hop=False):
            self.set_container_initialized(Compute.get_instance_local_ip(), user_id)
        else:
            # redirect to an appropriate instance
            redirect_instance = Compute.get_redirect_instance_id()
            if redirect_instance is not None:
                redirect_ip = Compute.get_instance_local_ip(redirect_instance)
                self.set_redirect_instance_id(redirect_ip)
        self.redirect('/')

    def post_auth_store_credentials(self, user_id, authtype, credtok):
        # TODO: make this generic for other authentication/authorization modes
        jbuser = JBoxUserV2(user_id, create=True)
        jbuser.set_gtok(base64.b64encode(credtok))
        jbuser.save()
        self.redirect('/')
        return


class JBPluginUI(LoggerMixin):
    """ Provide UI widgets/sections in a JuliaBox session.

    - `JBPluginUI.JBP_UI_SESSION_HEAD`, `JBPluginUI.JBP_UI_AUTH_BTN` and `JBPluginUI.JBP_UI_CONFIG_SECTION`:
        Type `JBP_UI_SESSION_HEAD` is included in the head section of the session screen.
        Type `JBP_UI_AUTH_BTN` is a login widget/button displayed on the JuliaBox login screen.
        Type `JBP_UI_CONFIG_SECTION` included as a section in the JuliaBox configuration screen.
        All UI providers must implement the following method.
        - `get_template(plugin_type)`: Return path to a template with the corresponding section/widget.
    """

    __metaclass__ = JBoxPluginType

    JBP_UI_CONFIG_SECTION = 'ui.config.section'
    JBP_UI_AUTH_BTN = 'ui.auth.btn'
    JBP_UI_SESSION_HEAD = 'ui.session.head'

    @staticmethod
    def create_include_files():
        JBPluginUI._gen_include(JBPluginUI.JBP_UI_CONFIG_SECTION, "admin")
        JBPluginUI._gen_include(JBPluginUI.JBP_UI_AUTH_BTN, "auth")
        JBPluginUI._gen_include(JBPluginUI.JBP_UI_SESSION_HEAD, "session")

    @staticmethod
    def _gen_include(plugin_type, plugin_type_name):
        # TODO: make template location configurable. For now, www must be located under engine folder.
        incl_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "www", plugin_type_name + "_modules.tpl")
        with open(incl_file_path, 'w') as incl_file:
            for plugin in JBPluginUI.jbox_get_plugins(plugin_type):
                JBPluginUI.log_info("Found %s plugin %r provides %r", plugin_type_name, plugin, plugin.provides)
                template_file = plugin.get_template(plugin_type)
                if template_file is None:
                    JBPluginUI.log_info("No %s template provided by %r", plugin_type_name, plugin)
                else:
                    incl_file.write('{%% module Template("%s") %%}\n' % (template_file,))


class JBPluginHandler(JBoxHandler):
    """ Provides additional request handler for session manager.

    - `JBPluginHandler.JBP_HANDLER`, `JBPluginHandler.JBP_HANDLER_AUTH, JBPluginHandler.JBP_HANDLER_AUTH_ZERO, JBPluginHandler.JBP_HANDLER_AUTH_GOOGLE`:
        Provides a request handler that can be registered with tornado.
        - `register(app)`: register self with tornado application to handle the desired URI
    - `JBPluginHandler.JBP_JS_TOP`:
        Provides path to a javascript file to be included in the top level window.
    """

    __metaclass__ = JBoxPluginType

    JBP_HANDLER = 'handler'
    JBP_HANDLER_AUTH = 'handler.auth'
    JBP_HANDLER_AUTH_ZERO = 'handler.auth.zero'
    JBP_HANDLER_AUTH_GOOGLE = 'handler.auth.google'
    JBP_JS_TOP = 'handler.js.top'

    JBP_HANDLER_POST_AUTH = 'handler.post_auth'

    PLUGIN_JAVASCRIPTS = []

    @staticmethod
    def add_plugin_handlers(app):
        for plugin in JBPluginHandler.jbox_get_plugins(JBPluginHandler.JBP_HANDLER):
            JBPluginHandler.log_info("Found plugin %r provides %r", plugin, plugin.provides)
            plugin.register(app)

        for plugin in JBPluginHandler.jbox_get_plugins(JBPluginHandler.JBP_JS_TOP):
            JBPluginHandler.log_info("Found plugin %r provides %r", plugin, plugin.provides)
            JBPluginHandler.PLUGIN_JAVASCRIPTS.append(plugin.get_js())
