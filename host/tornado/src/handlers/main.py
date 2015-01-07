import json
import base64
import httplib2

from oauth2client.client import OAuth2Credentials

from handlers.handler_base import JBoxHandler

from jbox_util import unique_sessname
from jbox_crypto import signstr
from db.user_v2 import JBoxUserV2
from jbox_container import JBoxContainer


class MainHandler(JBoxHandler):
    MSG_PENDING_ACTIVATION = "We are experiencing heavy traffic right now, and have put new registrations on hold. " + \
                             "Please try again in a few hours. " + \
                             "We will also send you an email as things quieten down and your account is enabled."

    def get(self):
        jbox_cookie = self.get_session_cookie()

        if None == jbox_cookie:
            pending_activation = self.get_argument('pending_activation', None)
            if pending_activation is not None:
                state = self.state(success=MainHandler.MSG_PENDING_ACTIVATION,
                                   pending_activation=True,
                                   user_id=pending_activation)
            else:
                state = self.state()
            self.rendertpl("index.tpl", cfg=self.config(), state=state)
        else:
            user_id = jbox_cookie['u']

            if self.is_loading():
                is_ajax = self.get_argument('monitor_loading', None) is not None
                if is_ajax:
                    self.do_monitor_loading_ajax(user_id)
                else:
                    self.do_monitor_loading(user_id)
            else:
                self.chk_and_launch_docker(user_id)

    def is_loading(self):
        return self.get_cookie('loading') is not None

    def do_monitor_loading_ajax(self, user_id):
        sessname = unique_sessname(user_id)
        self.log_debug("AJAX monitoring loading of session [%s] user[%s]...", sessname, user_id)
        cont = JBoxContainer.get_by_name(sessname)
        if (cont is None) or (not cont.is_running()):
            loading_step = int(self.get_cookie("loading", 0))
            if loading_step > 30:
                self.write({'code': -1})
                return

            loading_step += 1
            self.set_cookie("loading", str(loading_step))
            self.write({'code': 0})
        else:
            self.write({'code': 1})

    def do_monitor_loading(self, user_id):
        sessname = unique_sessname(user_id)
        self.log_debug("Monitoring loading of session [%s] user[%s]...", sessname, user_id)
        cont = JBoxContainer.get_by_name(sessname)
        if (cont is None) or (not cont.is_running()):
            loading_step = int(self.get_cookie("loading", 0))
            if loading_step > 30:
                self.clear_container_cookies()
                self.rendertpl("index.tpl", cfg=self.config(),
                               state=self.state(
                                   error='Could not start your instance! Please try again.',
                                   pending_activation=False,
                                   user_id=user_id))
                return
            else:
                loading_step += 1

            self.set_cookie("loading", str(loading_step))
            self.rendertpl("loading.tpl", user_id=user_id)
        else:
            if self.config("gauth"):
                jbuser = JBoxUserV2(user_id)
                creds = jbuser.get_gtok()
                if creds is not None:
                    try:
                        creds_json = json.loads(base64.b64decode(creds))
                        creds_json = self.renew_creds(creds_json)
                        authtok = creds_json['access_token']
                    except:
                        self.log_info("stale stored creds. will renew on next use. user: " + user_id)
                        creds = None
                        authtok = None
                else:
                    authtok = None
            else:
                creds = None
                authtok = None

            (shellport, uplport, ipnbport) = cont.get_host_ports()
            sign = signstr(sessname + str(shellport) + str(uplport) + str(ipnbport), self.config("sesskey"))

            self.clear_cookie("loading")
            self.set_container_cookies({
                "sessname": sessname,
                "hostshell": shellport,
                "hostupload": uplport,
                "hostipnb": ipnbport,
                "sign": sign
            })
            self.set_lb_tracker_cookie()
            self.rendertpl("ipnbsess.tpl", sessname=sessname, cfg=self.config(), creds=creds, authtok=authtok,
                           user_id=user_id)

    def chk_and_launch_docker(self, user_id):
        nhops = int(self.get_argument('h', 0))
        numhopmax = self.config('numhopmax', 0)
        max_hop = nhops > numhopmax
        launched = self.try_launch_container(user_id, max_hop=max_hop)

        if launched:
            self.set_loading_state(user_id)
            self.rendertpl("loading.tpl", stage=1, user_id=user_id)
            return

        self.unset_affinity()
        self.log_debug("at hop %d for user %s", nhops, user_id)
        if max_hop:
            self.rendertpl("index.tpl", cfg=self.config(), state=self.state(
                error="Maximum number of JuliaBox instances active. Please try after sometime.", success=''))
        else:
            self.redirect('/?h=' + str(nhops + 1))

    @staticmethod
    def renew_creds(creds):
        creds = OAuth2Credentials.from_json(json.dumps(creds))
        http = httplib2.Http(disable_ssl_certificate_validation=True)  # pass cacerts otherwise
        creds.refresh(http)
        creds = json.loads(creds.to_json())
        return creds

    @staticmethod
    def state(**kwargs):
        s = dict(error="", success="", info="", pending_activation=False, user_id="")
        s.update(**kwargs)
        return s

