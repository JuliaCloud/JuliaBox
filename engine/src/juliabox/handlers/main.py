import json
import base64
import httplib2

from oauth2client.client import OAuth2Credentials

from handler_base import JBoxHandler, JBoxHandlerPlugin
from juliabox.jbox_util import unique_sessname, JBoxCfg
from juliabox.jbox_crypto import signstr
from juliabox.db.user_v2 import JBoxUserV2
from juliabox.jbox_container import JBoxContainer
from juliabox.cloud.aws import CloudHost


class MainHandler(JBoxHandler):
    MSG_PENDING_ACTIVATION = "We are experiencing heavy traffic right now, and have put new registrations on hold. " + \
                             "Please try again in a few hours. " + \
                             "We will also send you an email as things quieten down and your account is enabled."

    def get(self):
        user_id = self.get_user_id()

        if None == user_id:
            pending_activation = self.get_argument('pending_activation', None)
            if pending_activation is not None:
                state = self.state(success=MainHandler.MSG_PENDING_ACTIVATION,
                                   pending_activation=True,
                                   user_id=pending_activation)
            else:
                state = self.state()
            self.rendertpl("index.tpl", cfg=JBoxCfg.nv, state=state)
        else:
            if self.is_loading():
                is_ajax = self.get_argument('monitor_loading', None) is not None
                if is_ajax:
                    self.do_monitor_loading_ajax(user_id)
                else:
                    self.do_monitor_loading(user_id)
            else:
                self.chk_and_launch_docker(user_id)

    def is_loading(self):
        return self.get_loading_state() is not None

    def do_monitor_loading_ajax(self, user_id):
        sessname = unique_sessname(user_id)
        self.log_debug("AJAX monitoring loading of session [%s] user[%s]...", sessname, user_id)
        cont = JBoxContainer.get_by_name(sessname)
        if (cont is None) or (not cont.is_running()):
            loading_step = int(self.get_loading_state(), 0)
            if loading_step > 30:
                self.log_error("Could not start instance. Session [%s] for user [%s] didn't load.", sessname, user_id)
                self.write({'code': -1})
                return

            loading_step += 1
            self.set_loading_state(loading_step)
            self.write({'code': 0})
        else:
            self.write({'code': 1})

    def do_monitor_loading(self, user_id):
        sessname = unique_sessname(user_id)
        self.log_debug("Monitoring loading of session [%s] user[%s]...", sessname, user_id)
        cont = JBoxContainer.get_by_name(sessname)
        if (cont is None) or (not cont.is_running()):
            loading_step = int(self.get_loading_state(), 0)
            if loading_step > 30:
                self.log_error("Could not start instance. Session [%s] for user [%s] didn't load.", sessname, user_id)
                self.clear_container()
                self.rendertpl("index.tpl", cfg=JBoxCfg.nv,
                               state=self.state(
                                   error='Could not start your instance! Please try again.',
                                   pending_activation=False,
                                   user_id=user_id))
                return
            else:
                loading_step += 1

            self.set_loading_state(loading_step)
            self.rendertpl("loading.tpl",
                           user_id=user_id,
                           cfg=JBoxCfg.nv,
                           js_includes=JBoxHandlerPlugin.PLUGIN_JAVASCRIPTS)
        else:
            (shellport, uplport, ipnbport) = cont.get_host_ports()

            self.set_container_ports({
                JBoxHandler.COOKIE_PORT_SHELL: shellport,
                JBoxHandler.COOKIE_PORT_UPL: uplport,
                JBoxHandler.COOKIE_PORT_IPNB: ipnbport
            })
            self.clear_loading()

            self.rendertpl("ipnbsess.tpl",  sessname=sessname, cfg=JBoxCfg.nv, user_id=user_id,
                           plugin_features=json.dumps(self.application.settings["plugin_features"]),
                           js_includes=JBoxHandlerPlugin.PLUGIN_JAVASCRIPTS)

    def chk_and_launch_docker(self, user_id):
        if self.redirect_to_logged_in_instance(user_id):
            return

        nhops = int(self.get_argument('h', 0))
        numhopmax = JBoxCfg.get('numhopmax', 0)
        max_hop = nhops > numhopmax
        launched = self.try_launch_container(user_id, max_hop=max_hop)

        if launched:
            self.set_container_initialized(CloudHost.instance_local_ip(), user_id)
            self.rendertpl("loading.tpl",
                           user_id=user_id,
                           cfg=JBoxCfg.nv,
                           js_includes=JBoxHandlerPlugin.PLUGIN_JAVASCRIPTS)
            return

        self.unset_affinity()
        self.log_debug("at hop %d for user %s", nhops, user_id)
        if max_hop:
            self.log_error("Server maxed out. Can't launch container at hop %d for user %s", nhops, user_id)
            self.rendertpl("index.tpl", cfg=JBoxCfg.nv, state=self.state(
                error="Maximum number of JuliaBox instances active. Please try after sometime.", success=''))
        else:
            redirect_instance = CloudHost.get_redirect_instance_id()
            if redirect_instance is not None:
                redirect_ip = CloudHost.instance_local_ip(redirect_instance)
                self.set_redirect_instance_id(redirect_ip)
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

