import json
import base64
import traceback
import pytz
import datetime

import isodate
from tornado.web import RequestHandler

from juliabox.jbox_util import LoggerMixin, unique_sessname
from juliabox.jbox_container import JBoxContainer
from juliabox.jbox_tasks import JBoxAsyncJob
from juliabox.jbox_crypto import signstr
from juliabox.cloud.aws import CloudHost
from juliabox.db import is_proposed_cluster_leader


class JBoxHandler(RequestHandler, LoggerMixin):
    _config = None
    AUTH_COOKIE = 'juliabox'
    AUTH_VALID_DAYS = 30
    AUTH_VALID_SECS = (AUTH_VALID_DAYS * 24 * 60 * 60)

    def rendertpl(self, tpl, **kwargs):
        self.render("../../../www/" + tpl, **kwargs)

    @classmethod
    def configure(cls, cfg):
        cls._config = cfg

    @classmethod
    def config(cls, key=None, default=None):
        if key is None:
            return cls._config
        if key in cls._config:
            return cls._config[key]
        else:
            return default

    @classmethod
    def is_valid_req(cls, req):
        sessname = req.get_cookie("sessname")
        if None == sessname:
            return False
        sessname = sessname.replace('"', '')
        hostshell = req.get_cookie("hostshell").replace('"', '')
        hostupl = req.get_cookie("hostupload").replace('"', '')
        hostipnb = req.get_cookie("hostipnb").replace('"', '')
        signval = req.get_cookie("sign").replace('"', '')

        sign = signstr(sessname + hostshell + hostupl + hostipnb, cls._config["sesskey"])
        if sign != signval:
            cls.log_info('not valid req. signature not matching')
            return False
        if not JBoxContainer.is_valid_container("/" + sessname, (hostshell, hostupl, hostipnb)):
            cls.log_info('not valid req. container deleted or ports not matching')
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
        self.clear_container_cookies()
        self.clear_lb_tracker_cookie()
        self.set_header('Connection', 'close')
        self.request.connection.no_keep_alive = True

    def set_loading_state(self, user_id):
        sessname = unique_sessname(user_id)
        sign = signstr(sessname + '000', self.config("sesskey"))
        self.set_container_cookies({
            "sessname": sessname,
            "hostshell": 0,
            "hostupload": 0,
            "hostipnb": 0,
            "loading": 1,
            "sign": sign
        })
        self.set_lb_tracker_cookie()

    def clear_container_cookies(self):
        for name in ["sessname", "hostshell", "hostupload", "hostipnb", "sign", "loading"]:
            self.clear_cookie(name)

    def clear_lb_tracker_cookie(self):
        for name in ["AWSELB", "lb"]:
            self.clear_cookie(name)

    def set_container_cookies(self, cookies):
        max_session_time = self.config('expire')
        if max_session_time == 0:
            max_session_time = JBoxHandler.AUTH_VALID_SECS
        expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=max_session_time)

        for n, v in cookies.iteritems():
            self.set_cookie(n, str(v), expires=expires)

    def set_lb_tracker_cookie(self):
        self.set_cookie('lb', signstr(CloudHost.instance_id(), self.config('sesskey')), expires_days=30)

    def get_session_cookie(self):
        try:
            jbox_cookie = self.get_cookie(JBoxHandler.AUTH_COOKIE)
            if jbox_cookie is None:
                return None
            jbox_cookie = json.loads(base64.b64decode(jbox_cookie))
            sign = signstr(jbox_cookie['u'] + jbox_cookie['t'], JBoxHandler._config['sesskey'])
            if sign != jbox_cookie['x']:
                self.log_info("signature mismatch for " + jbox_cookie['u'])
                return None

            d = isodate.parse_datetime(jbox_cookie['t'])
            age = (datetime.datetime.now(pytz.utc) - d).total_seconds()
            if age > JBoxHandler.AUTH_VALID_SECS:
                self.log_info("cookie older than allowed days: " + jbox_cookie['t'])
                return None
            return jbox_cookie
        except:
            self.log_error("exception while reading cookie")
            traceback.print_exc()
            return None

    def set_session_cookie(self, user_id):
        t = datetime.datetime.now(pytz.utc).isoformat()
        sign = signstr(user_id + t, self.config('sesskey'))

        jbox_cookie = {'u': user_id, 't': t, 'x': sign}
        self.set_cookie(JBoxHandler.AUTH_COOKIE, base64.b64encode(json.dumps(jbox_cookie)))
