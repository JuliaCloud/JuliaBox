__author__ = 'tan'
import datetime
import json
import os
import base64
import httplib2

import tornado
import tornado.web
import tornado.gen
import tornado.httpclient
from tornado.auth import GoogleOAuth2Mixin
from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI
from oauth2client.client import OAuth2Credentials, _extract_id_token

from juliabox.jbox_util import JBoxCfg
from juliabox.handlers import JBPluginHandler, JBPluginUI
from juliabox.db import JBoxUserV2


class GoogleAuthUIHandler(JBPluginUI):
    provides = [JBPluginUI.JBP_UI_AUTH_BTN, JBPluginUI.JBP_UI_SESSION_HEAD]
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def get_template(plugin_type):
        if plugin_type == JBPluginUI.JBP_UI_AUTH_BTN:
            return os.path.join(GoogleAuthUIHandler.TEMPLATE_PATH, "google_login_btn.tpl")
        if plugin_type == JBPluginUI.JBP_UI_SESSION_HEAD:
            return os.path.join(GoogleAuthUIHandler.TEMPLATE_PATH, "google_login_session.tpl")

    @staticmethod
    def get_updated_token(handler):
        user_id = handler.get_user_id()
        jbuser = JBoxUserV2(user_id)
        creds = jbuser.get_gtok()
        authtok = None
        if creds is not None:
            try:
                creds_json = json.loads(base64.b64decode(creds))
                creds_json = GoogleAuthUIHandler._renew_creds(creds_json)
                authtok = creds_json['access_token']
            except:
                GoogleAuthUIHandler.log_warn("stale stored creds. will renew on next use. user: " + user_id)
                creds = None
                authtok = None
        return {'creds': creds, 'authtok': authtok, 'user_id': user_id}

    @staticmethod
    def _renew_creds(creds):
        creds = OAuth2Credentials.from_json(json.dumps(creds))
        http = httplib2.Http(disable_ssl_certificate_validation=True)  # pass cacerts otherwise
        creds.refresh(http)
        creds = json.loads(creds.to_json())
        return creds


class GoogleAuthHandler(JBPluginHandler, GoogleOAuth2Mixin):
    provides = [JBPluginHandler.JBP_HANDLER,
                JBPluginHandler.JBP_HANDLER_AUTH,
                JBPluginHandler.JBP_HANDLER_AUTH_GOOGLE]

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxauth/google/", GoogleAuthHandler)])
        app.settings["google_oauth"] = JBoxCfg.get('google_oauth')
        # GoogleAuthHandler.log_debug("setting google_oauth: %r", app.settings["google_oauth"])

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        # self_redirect_uri should be similar to  'http://<host>/jboxauth/google/'
        self_redirect_uri = self.request.full_url()
        idx = self_redirect_uri.index("jboxauth/google/")
        self_redirect_uri = self_redirect_uri[0:(idx + len("jboxauth/google/"))]

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

            if state == 'store_creds':
                creds = self.make_credentials(user)
                credtok = creds.to_json()
                self.post_auth_store_credentials(user_id, "gdrive", credtok)
                return
            else:
                self.post_auth_launch_container(user_id)
                return
        else:
            if state == 'ask_gdrive':
                user_id = self.get_user_id()
                scope = ['https://www.googleapis.com/auth/drive']
                extra_params = {'approval_prompt': 'force', 'access_type': 'offline',
                                'login_hint': user_id, 'include_granted_scopes': 'true',
                                'state': 'store_creds'}
            else:
                scope = ['profile', 'email']
                extra_params = {'approval_prompt': 'auto'}

            yield self.authorize_redirect(redirect_uri=self_redirect_uri,
                                          client_id=self.settings['google_oauth']['key'],
                                          scope=scope,
                                          response_type='code',
                                          extra_params=extra_params)

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