import json
import os
import urllib
import functools
import traceback
import tornado
import tornado.web
import tornado.gen
import tornado.httpclient
import tornado.escape
import tornado.httputil
from tornado.auth import OAuth2Mixin, _auth_return_future, AuthError

from juliabox.jbox_util import JBoxCfg, gen_random_secret
from juliabox.handlers import JBPluginHandler, JBPluginUI
from juliabox.db import JBoxUserProfile

__author__ = 'tan'


class LinkedInAuthUIHandler(JBPluginUI):
    provides = [JBPluginUI.JBP_UI_AUTH_BTN]
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def get_template(plugin_type):
        if plugin_type == JBPluginUI.JBP_UI_AUTH_BTN:
            return os.path.join(LinkedInAuthUIHandler.TEMPLATE_PATH, "linkedin_login_btn.tpl")


class LinkedInAuthHandler(JBPluginHandler, OAuth2Mixin):
    provides = [JBPluginHandler.JBP_HANDLER,
                JBPluginHandler.JBP_HANDLER_AUTH,
                JBPluginHandler.JBP_HANDLER_AUTH_LINKEDIN]

    _OAUTH_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
    _OAUTH_ACCESS_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    _OAUTH_NO_CALLBACKS = False
    _OAUTH_SETTINGS_KEY = 'linkedin_oauth'
    PROFILE_ATTRS = ['id',
                     'num-connections',
                     'picture-url',
                     'first-name',
                     'last-name',
                     'email-address',
                     'location',
                     'industry']
    PROFILE_URL = 'https://api.linkedin.com/v1/people/~' + \
                  ':(' + ','.join(PROFILE_ATTRS) + ')' + \
                  '?format=json'

    SCOPES = ['r_basicprofile r_emailaddress']

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxauth/linkedin/", LinkedInAuthHandler)])
        app.settings["linkedin_oauth"] = JBoxCfg.get('linkedin_oauth')

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        # self_redirect_uri should be similar to  'http://<host>/jboxauth/linkedin/'
        self_redirect_uri = self.request.full_url()
        idx = self_redirect_uri.index("jboxauth/linkedin/")
        self_redirect_uri = self_redirect_uri[0:(idx + len("jboxauth/linkedin/"))]

        code = self.get_argument('code', False)
        if code is not False:
            state = self.get_argument('state', None)
            secret = self.get_state_cookie()
            if not state or not secret or state != secret:
                self.log_warn("LinkedIn auth:  Invalid login attempt")
                self.rendertpl("index.tpl", cfg=JBoxCfg.nv, state=self.state(
                    error="Invalid login request", success=""))
                return
            user = yield self.get_authenticated_user(redirect_uri=self_redirect_uri, code=code)
            user_info = yield self.get_user_info(user)
            try:
                self.update_user_profile(user_info)
            except:
                self.log_error("exception while capturing user profile")
                traceback.print_exc()
            user_id = user_info['emailAddress']
            LinkedInAuthHandler.log_debug("logging in user_id=%r", user_id)
            self.post_auth_launch_container(user_id)
            return
        else:
            error = self.get_argument('error', False)
            if error is not False:
                error_description = self.get_argument('error_description', '')
                LinkedInAuthHandler.log_info("Linked in auth error: %r, %r", error, error_description)
                self.redirect(self_redirect_uri[0:idx])
                return
            else:
                state = gen_random_secret()
                self.set_state_cookie(state)
                yield self.authorize_redirect(redirect_uri=self_redirect_uri,
                                              client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                                              scope=self.SCOPES,
                                              response_type='code',
                                              extra_params={'state': state})

    @_auth_return_future
    def get_user_info(self, user, callback):
        http = self.get_auth_http_client()
        auth_string = "Bearer %s" % user['access_token']
        headers = {
            "Authorization": auth_string,
            "User-Agent": "JuliaBox Tornado Python client"
        }
        http.fetch(LinkedInAuthHandler.PROFILE_URL,
                   functools.partial(self._on_user_info, callback),
                   headers=headers)

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, code, callback):
        """Handles GitHub login, returning a user object.
        """
        http = self.get_auth_http_client()
        body = urllib.urlencode({
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": self.settings[self._OAUTH_SETTINGS_KEY]['key'],
            "client_secret": self.settings[self._OAUTH_SETTINGS_KEY]['secret']
        })

        http.fetch(self._OAUTH_ACCESS_TOKEN_URL,
                   functools.partial(self._on_access_token, callback),
                   method="POST", headers={'Content-Type': 'application/x-www-form-urlencoded'}, body=body)

    def _on_user_info(self, future, response):
        if response.error:
            future.set_exception(AuthError('LinkedIn auth error: %s [%s]' % (str(response), response.body)))
            return
        user_info = json.loads(response.body)
        future.set_result(user_info)

    def _on_access_token(self, future, response):
        """Callback function for the exchange to the access token."""
        if response.error:
            future.set_exception(AuthError('LinkedIn auth error: %s' % str(response)))
            return
        args = json.loads(response.body)
        future.set_result(args)

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return tornado.httpclient.AsyncHTTPClient()

    def update_user_profile(self, user_info):
        user_id = user_info['emailAddress']
        profile = JBoxUserProfile(user_id, create=True)
        updated = False

        if 'firstName' in user_info:
            val = user_info['firstName']
            if profile.can_set(JBoxUserProfile.ATTR_FIRST_NAME, val):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_FIRST_NAME, val, 'linkedin')

        if 'lastName' in user_info:
            val = user_info['lastName']
            if profile.can_set(JBoxUserProfile.ATTR_LAST_NAME, val):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_LAST_NAME, val, 'linkedin')

        if 'industry' in user_info:
            val = user_info['industry']
            if profile.can_set(JBoxUserProfile.ATTR_INDUSTRY, val):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_INDUSTRY, val, 'linkedin')

        if 'location' in user_info:
            loc = user_info['location']
            if 'name' in loc:
                val = loc['name']
                if profile.can_set(JBoxUserProfile.ATTR_LOCATION, val):
                    updated |= profile.set_profile(JBoxUserProfile.ATTR_LOCATION, val, 'linkedin')
            if 'country' in loc:
                country = loc['country']
                if 'code' in country:
                    val = country['code'].lower()
                    if profile.can_set(JBoxUserProfile.ATTR_COUNTRY, val):
                        updated |= profile.set_profile(JBoxUserProfile.ATTR_COUNTRY, val, 'linkedin')

        xff = self.request.headers.get('X-Forwarded-For')
        client_ip = xff.split(',')[0] if xff else self.get_client_ip()

        if profile.can_set(JBoxUserProfile.ATTR_IP, client_ip):
            updated |= profile.set_profile(JBoxUserProfile.ATTR_IP, client_ip, 'http')

        if updated:
            LinkedInAuthHandler.log_debug("updating ip=%r and profile=%r", client_ip, user_info)
            profile.save()
