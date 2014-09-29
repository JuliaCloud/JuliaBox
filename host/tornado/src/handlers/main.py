import datetime
import json
import base64
import httplib2

from oauth2client.client import OAuth2Credentials

from handlers.handler_base import JBoxHandler

from jbox_util import unique_sessname, CloudHelper
from jbox_crypto import signstr
from handlers.auth import AuthHandler
from db.user_v2 import JBoxUserV2
from db.invites import JBoxInvite
from jbox_container import JBoxContainer


class MainHandler(JBoxHandler):
    def get(self):
        jbox_cookie = AuthHandler.get_session_cookie(self)

        if self.config("invite_only"):
            if self.get_argument("invite", False):
                self.set_cookie("is_invite", "yes")
                self.redirect('/hostlaunchipnb/')
                return

        if None == jbox_cookie:
            which_msg = int(self.get_argument("_msg", JBoxUserV2.ACTIVATION_NONE))
            if self.get_argument("_msg", "") != "":
                self.clear_cookie("is_invite")
                if which_msg == JBoxUserV2.ACTIVATION_GRANTED:
                    msg = "Your account has already been approved"
                elif which_msg == JBoxUserV2.ACTIVATION_REQUESTED:
                    msg = "You have already registered for an invite"
                else:
                    msg = "Thank you for your interest! We will get back to you with an invitation soon."
                state = self.state(success=msg)
            else:
                state = self.state()
            self.rendertpl("index.tpl", cfg=self.config(), state=state)
        else:
            user_id = jbox_cookie['u']
            sessname = unique_sessname(user_id)

            if self.config("gauth"):
                try:
                    jbuser = JBoxUserV2(user_id)
                except:
                    # stale cookie. we don't have the user in our database anymore
                    self.log_info("stale cookie. we don't have the user in our database anymore. user: " + user_id)
                    self.redirect('/hostlaunchipnb/')
                    return

                if self.config("invite_only"):
                    code, status = jbuser.get_activation_state()
                    if status != JBoxUserV2.ACTIVATION_GRANTED:
                        invite_code = self.get_argument("invite_code", False)
                        if invite_code is not False:
                            try:
                                invite = JBoxInvite(invite_code)
                            except:
                                invite = None

                            if (invite is not None) and invite.is_invited(user_id):
                                jbuser.set_activation_state(invite_code, JBoxUserV2.ACTIVATION_GRANTED)
                                invite.increment_count()
                                invite.save()
                                jbuser.save()
                                self.redirect('/hostlaunchipnb/')
                                return
                            else:
                                error_msg = 'You entered an invalid invitation code. Try again or request a new invitation.'
                        else:
                            error_msg = 'Enter an invitation code to proceed.'

                        self.rendertpl("index.tpl", cfg=self.config(), state=self.state(
                            error=error_msg,
                            ask_invite_code=True, user_id=user_id))
                        return

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

            self.chk_and_launch_docker(sessname, creds, authtok, user_id)

    def clear_container_cookies(self):
        for name in ["sessname", "hostshell", "hostupload", "hostipnb", "sign"]:
            self.clear_cookie(name)

    def set_container_cookies(self, cookies):
        max_session_time = self.config('expire')
        if max_session_time == 0:
            max_session_time = AuthHandler.AUTH_VALID_SECS
        expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=max_session_time)

        for n, v in cookies.iteritems():
            self.set_cookie(n, str(v), expires=expires)

    def set_lb_tracker_cookie(self):
        self.set_cookie('lb', signstr(CloudHelper.instance_id(), self.config('sesskey')), expires_days=30)

    def chk_and_launch_docker(self, sessname, creds, authtok, user_id):
        cont = JBoxContainer.get_by_name(sessname)
        nhops = int(self.get_argument('h', 0))
        self.log_debug("got hop " + repr(nhops) + " for session " + repr(sessname))
        self.log_debug("have existing container for " + repr(sessname) + ": " + repr(None != cont))
        if cont is not None:
            self.log_debug("container running: " + str(cont.is_running()))

        if ((None == cont) or (not cont.is_running())) and (not CloudHelper.should_accept_session()):
            if None != cont:
                cont.backup()
                cont.delete()
            self.clear_container_cookies()
            self.set_header('Connection', 'close')
            self.request.connection.no_keep_alive = True
            if nhops > self.config('numhopmax', 0):
                self.rendertpl("index.tpl", cfg=self.config(), state=self.state(
                    error="Maximum number of JuliaBox instances active. Please try after sometime.", success=''))
            else:
                self.redirect('/?h=' + str(nhops + 1))
        else:
            cont = JBoxContainer.launch_by_name(sessname, user_id, True)
            (shellport, uplport, ipnbport) = cont.get_host_ports()
            sign = signstr(sessname + str(shellport) + str(uplport) + str(ipnbport), self.config("sesskey"))

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

    @staticmethod
    def renew_creds(creds):
        creds = OAuth2Credentials.from_json(json.dumps(creds))
        http = httplib2.Http(disable_ssl_certificate_validation=True)  # pass cacerts otherwise
        creds.refresh(http)
        creds = json.loads(creds.to_json())
        return creds

    @staticmethod
    def state(**kwargs):
        s = dict(error="", success="", info="", ask_invite_code=False, user_id="")
        s.update(**kwargs)
        return s

