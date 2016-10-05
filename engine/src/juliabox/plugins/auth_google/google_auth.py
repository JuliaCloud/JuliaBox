import datetime
import json
import os
import base64
import httplib2
import traceback
import functools
import urllib
import time

import tornado
import tornado.web
import tornado.gen
import tornado.httpclient
from tornado.auth import OAuth2Mixin, _auth_return_future, AuthError
from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI
from oauth2client.client import OAuth2Credentials, _extract_id_token

from juliabox.jbox_util import JBoxCfg, gen_random_secret
from juliabox.handlers import JBPluginHandler, JBPluginUI
from juliabox.db import JBoxUserV2, JBoxUserProfile

__author__ = 'tan'


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


class GoogleAuthHandler(JBPluginHandler, OAuth2Mixin):
    provides = [JBPluginHandler.JBP_HANDLER,
                JBPluginHandler.JBP_HANDLER_AUTH,
                JBPluginHandler.JBP_HANDLER_AUTH_GOOGLE]

    _OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _OAUTH_ACCESS_TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
    _OAUTH_NO_CALLBACKS = False
    _OAUTH_SETTINGS_KEY = 'google_oauth'

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxauth/google/", GoogleAuthHandler)])
        app.settings["google_oauth"] = JBoxCfg.get('google_oauth')
        # GoogleAuthHandler.log_debug("setting google_oauth: %r", app.settings["google_oauth"])

    @staticmethod
    def state(**kwargs):
        s = dict(error="", success="", info="",
                 pending_activation=False, user_id="")
        s.update(**kwargs)
        return s

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
            cookie = self.get_state_cookie()
            secret = None
            task = None
            if state:
                state = json.loads(base64.b64decode(state))
                secret = state.get('secret')
                task = state.get('task')

            if not cookie or not secret or cookie != secret:
                self.log_warn("GitHub auth:  Invalid login attempt")
                self.rendertpl("index.tpl", cfg=JBoxCfg.nv, state=self.state(
                    error="Invalid login request", success=""))
                return
            user = yield self.get_authenticated_user(redirect_uri=self_redirect_uri, code=code)
            if not user:
                self.rendertpl("index.tpl", cfg=JBoxCfg.nv, state=self.state(
                    error="Google authentication failed due to unexpected error.  Please try again.",
                    success=""))
                return

            user_info = None
            tries = 0
            while True:
                try:
                    user_info = yield self.get_user_info(user)
                    break
                except AuthError, e:
                    if e.args[1]["error"]["code"] != 500:
                        raise
                    if tries >= 2:
                        traceback.print_exc()
                        break
                    time.sleep(2 ** tries)
                    tries += 1

            if not user_info:
                self.rendertpl("index.tpl", cfg=JBoxCfg.nv, state=self.state(
                    error="Google authentication failed due to unexpected error.  Please try again.",
                    success=""))
                return
            try:
                self.update_user_profile(user_info)
            except:
                self.log_error("exception while capturing user profile")
                traceback.print_exc()
            user_id = user_info['email']

            if task == 'store_creds':
                creds = self.make_credentials(user)
                credtok = creds.to_json()
                self.post_auth_store_credentials(user_id, "gdrive", credtok)
                return
            else:
                self.post_auth_launch_container(user_id)
                return
        else:
            secret = gen_random_secret()
            new_state = {'secret': secret}
            if state == 'ask_gdrive':
                user_id = self.get_user_id()
                new_state['task'] = 'store_creds'
                scope = ['https://www.googleapis.com/auth/drive']
                extra_params = {'access_type': 'offline', 'prompt': 'consent',
                                'login_hint': user_id, 'include_granted_scopes': 'true'}
            else:
                scope = ['profile', 'email']
                extra_params = {'approval_prompt': 'auto'}

            extra_params['state'] = base64.b64encode(json.dumps(new_state))
            self.set_state_cookie(secret)
            yield self.authorize_redirect(redirect_uri=self_redirect_uri,
                                          client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                                          scope=scope,
                                          response_type='code',
                                          extra_params=extra_params)

    @_auth_return_future
    def get_user_info(self, user, callback):
        http = self.get_auth_http_client()
        auth_string = "%s %s" % (user['token_type'], user['access_token'])
        headers = {
            "Authorization": auth_string
        }
        http.fetch('https://www.googleapis.com/userinfo/v2/me',
                   functools.partial(self._on_user_info, callback),
                   headers=headers)

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, code, callback):
        """Handles Google login, returning a user object.
        """
        http = self.get_auth_http_client()
        body = urllib.urlencode({
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": self.settings[self._OAUTH_SETTINGS_KEY]['key'],
            "client_secret": self.settings[self._OAUTH_SETTINGS_KEY]['secret'],
            "grant_type": "authorization_code"
        })

        http.fetch(self._OAUTH_ACCESS_TOKEN_URL,
                   functools.partial(self._on_access_token, callback),
                   method="POST", headers={'Content-Type': 'application/x-www-form-urlencoded'}, body=body)

    def _on_user_info(self, future, response):
        if response.error:
            future.set_exception(AuthError('Google auth error: %s [%s]' %
                                           (str(response), response.body)), response)
            return
        user_info = json.loads(response.body)
        future.set_result(user_info)

    def _on_access_token(self, future, response):
        """Callback function for the exchange to the access token."""
        if response.error:
            future.set_exception(AuthError('Google auth error: %s [%s]' %
                                           (str(response), response.body)), response)
            return
        args = json.loads(response.body)
        if not args.has_key('access_token'):
            GoogleAuthHandler.log_error('Google auth error: Key `access_token` not found in response: %r\nResponse body: %r\nResponse headers: %r',
                                        args, response.body, list(response.headers.get_all()))
            future.set_result(None)
            return
        future.set_result(args)

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return tornado.httpclient.AsyncHTTPClient()

    def make_credentials(self, user):
        # return AccessTokenCredentials(user['access_token'], "juliabox")
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(user['expires_in']))
        id_token = _extract_id_token(user['id_token'])
        credential = OAuth2Credentials(
            access_token=user['access_token'],
            client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
            client_secret=self.settings[self._OAUTH_SETTINGS_KEY]['secret'],
            refresh_token=user['refresh_token'],
            token_expiry=token_expiry,
            token_uri=GOOGLE_TOKEN_URI,
            user_agent=None,
            revoke_uri=GOOGLE_REVOKE_URI,
            id_token=id_token,
            token_response=user)
        return credential

    def update_user_profile(self, user_info):
        user_id = user_info['email']
        profile = JBoxUserProfile(user_id, create=True)
        updated = False

        if 'given_name' in user_info:
            val = user_info['given_name']
            if profile.can_set(JBoxUserProfile.ATTR_FIRST_NAME, val):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_FIRST_NAME, val, 'google')

        if 'family_name' in user_info:
            val = user_info['family_name']
            if profile.can_set(JBoxUserProfile.ATTR_LAST_NAME, val):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_LAST_NAME, val, 'google')

        xff = self.request.headers.get('X-Forwarded-For')
        client_ip = xff.split(',')[0] if xff else self.get_client_ip()

        if profile.can_set(JBoxUserProfile.ATTR_IP, client_ip):
            updated |= profile.set_profile(JBoxUserProfile.ATTR_IP, client_ip, 'http')

        if updated:
            GoogleAuthHandler.log_debug("updating ip=%r and profile=%r", client_ip, user_info)
            profile.save()
