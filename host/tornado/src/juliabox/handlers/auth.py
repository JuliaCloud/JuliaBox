import base64
import datetime
import json

import tornado
import tornado.web
import tornado.gen
import tornado.httpclient
from tornado.auth import GoogleOAuth2Mixin
from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI
from oauth2client.client import OAuth2Credentials, _extract_id_token

from handler_base import JBoxHandler
from juliabox.db import JBoxUserV2, JBoxDynConfig
from juliabox.jbox_util import unquote
from juliabox.cloud.aws import CloudHost


class AuthHandler(JBoxHandler, GoogleOAuth2Mixin):
    CRED_STORE = {}

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        if not self.config("gauth"):
            sessname = unquote(self.get_argument("sessname"))
            self.set_session_cookie(sessname)
            self.redirect('/')
            return

        # self_redirect_uri should be similar to  'http://<host>/hostlaunchipnb/'
        self_redirect_uri = self.request.full_url()
        idx = self_redirect_uri.index("hostlaunchipnb/")
        self_redirect_uri = self_redirect_uri[0:(idx + len("hostlaunchipnb/"))]

        # state indicates the stage of auth during multistate auth
        state = self.get_argument('state', None)

        code = self.get_argument('code', False)
        if code is not False:
            user = yield self.get_authenticated_user(redirect_uri=self_redirect_uri, code=code)

            # get user info
            http = tornado.httpclient.AsyncHTTPClient()
            auth_string = "%s %s" % (user['token_type'], user['access_token'])
            response = yield http.fetch('https://www.googleapis.com/userinfo/v2/me',
                                        headers={"Authorization": auth_string})
            user_info = json.loads(response.body)

            user_id = user_info['email']

            jbuser = JBoxUserV2(user_id, create=True)
            if state == 'store_creds':
                creds = self.make_credentials(user)
                jbuser.set_gtok(base64.b64encode(creds.to_json()))
                jbuser.save()
                #self.log_info(str(user))
                #self.log_info(creds.to_json())
                self.redirect('/')
                return
            else:
                if not AuthHandler.is_user_activated(jbuser):
                    self.redirect('/?pending_activation=' + user_id)
                    return

                self.set_session_cookie(user_id)
                if jbuser.is_new:
                    jbuser.save()

                if self.try_launch_container(user_id, max_hop=False):
                    self.set_loading_state(user_id)
                self.redirect('/')
                return
        else:
            if state == 'ask_gdrive':
                jbox_cookie = self.get_session_cookie()
                scope = ['https://www.googleapis.com/auth/drive']
                extra_params = {'approval_prompt': 'force', 'access_type': 'offline',
                                'login_hint': jbox_cookie['u'], 'include_granted_scopes': 'true',
                                'state': 'store_creds'}
            else:
                scope = ['profile', 'email']
                extra_params = {'approval_prompt': 'auto'}

            yield self.authorize_redirect(redirect_uri=self_redirect_uri,
                                          client_id=self.settings['google_oauth']['key'],
                                          scope=scope,
                                          response_type='code',
                                          extra_params=extra_params)

    @staticmethod
    def is_user_activated(jbuser):
        reg_allowed = JBoxDynConfig.get_allow_registration(CloudHost.INSTALL_ID)
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

    def make_credentials(self, user):
        # return AccessTokenCredentials(user['access_token'], "juliabox")
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(user['expires_in']))
        id_token = _extract_id_token(user['id_token'])
        credential = OAuth2Credentials(
            access_token=user['access_token'],
            client_id=self.settings['google_oauth']['key'],
            client_secret=self.settings['google_oauth']['secret'],
            refresh_token=user['refresh_token'],
            token_expiry=token_expiry,
            token_uri=GOOGLE_TOKEN_URI,
            user_agent=None,
            revoke_uri=GOOGLE_REVOKE_URI,
            id_token=id_token,
            token_response=user)
        return credential
