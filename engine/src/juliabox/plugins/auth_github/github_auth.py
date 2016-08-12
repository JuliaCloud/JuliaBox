import json
import os
import urllib
import functools

import tornado
import tornado.web
import tornado.gen
import tornado.httpclient
import tornado.escape
import tornado.httputil
from tornado.auth import OAuth2Mixin, _auth_return_future, AuthError

from juliabox.jbox_util import JBoxCfg
from juliabox.handlers import JBPluginHandler, JBPluginUI
from juliabox.db import JBoxUserProfile

__author__ = 'tan'


class GitHubAuthUIHandler(JBPluginUI):
    provides = [JBPluginUI.JBP_UI_AUTH_BTN]
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def get_template(plugin_type):
        if plugin_type == JBPluginUI.JBP_UI_AUTH_BTN:
            return os.path.join(GitHubAuthUIHandler.TEMPLATE_PATH, "github_login_btn.tpl")


class GitHubAuthHandler(JBPluginHandler, OAuth2Mixin):
    provides = [JBPluginHandler.JBP_HANDLER,
                JBPluginHandler.JBP_HANDLER_AUTH,
                JBPluginHandler.JBP_HANDLER_AUTH_GITHUB]

    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    _OAUTH_NO_CALLBACKS = False
    _OAUTH_SETTINGS_KEY = 'github_oauth'

    SCOPES = ['user:email']
    EXTRA_PARAMS = {'allow_signup': 'true'}

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxauth/github/", GitHubAuthHandler)])
        app.settings["github_oauth"] = JBoxCfg.get('github_oauth')

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        # self_redirect_uri should be similar to  'http://<host>/jboxauth/github/'
        self_redirect_uri = self.request.full_url()
        idx = self_redirect_uri.index("jboxauth/github/")
        self_redirect_uri = self_redirect_uri[0:(idx + len("jboxauth/github/"))]

        code = self.get_argument('code', False)
        if code is not False:
            user = yield self.get_authenticated_user(redirect_uri=self_redirect_uri, code=code)
            user_info = yield self.get_user_info(user)
            self.update_user_profile(user_info)
            user_id = user_info['email']
            GitHubAuthHandler.log_debug("logging in user_id=%r", user_id)
            self.post_auth_launch_container(user_id)
            return
        else:
            yield self.authorize_redirect(redirect_uri=self_redirect_uri,
                                          client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                                          scope=self.SCOPES,
                                          response_type='code',
                                          extra_params=self.EXTRA_PARAMS)

    @_auth_return_future
    def get_user_info(self, user, callback):
        http = self.get_auth_http_client()
        auth_string = "%s %s" % (user['token_type'], user['access_token'])
        headers = {
            "Authorization": auth_string,
            "User-Agent": "JuliaBox Tornado Python client"
        }
        http.fetch('https://api.github.com/user',
                   functools.partial(self._on_user_info, callback),
                   headers=headers)

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, code, callback):
        """Handles GitHub login, returning a user object.
        """
        http = self.get_auth_http_client()
        body = urllib.urlencode({
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
            future.set_exception(AuthError('GitHub auth error: %s [%s]' % (str(response), response.body)))
            return
        user_info = json.loads(response.body)
        future.set_result(user_info)

    def _on_access_token(self, future, response):
        """Callback function for the exchange to the access token."""
        if response.error:
            future.set_exception(AuthError('GitHub auth error: %s' % str(response)))
            return
        args = dict()
        tornado.httputil.parse_body_arguments(response.headers.get("Content-Type"), response.body, args, None)
        args['access_token'] = args['access_token'][0]
        args['token_type'] = args['token_type'][0]
        future.set_result(args)

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return tornado.httpclient.AsyncHTTPClient()

    def update_user_profile(self, user_info):
        user_id = user_info['email']
        profile = JBoxUserProfile(user_id, create=True)
        updated = False

        if 'location' in user_info:
            val = user_info['location']
            if profile.can_set(JBoxUserProfile.ATTR_LOCATION, val):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_LOCATION, val, 'github')

        if 'company' in user_info:
            val = user_info['company']
            if profile.can_set(JBoxUserProfile.ATTR_ORGANIZATION, val):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_ORGANIZATION, val, 'github')

        if 'name' in user_info:
            val = user_info['name'].split(' ', 1)
            firstname = val[0]
            lastname = val[1] if len(val) > 1 else ''

            if profile.can_set(JBoxUserProfile.ATTR_FIRST_NAME, firstname):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_FIRST_NAME, firstname, 'github')

            if profile.can_set(JBoxUserProfile.ATTR_LAST_NAME, lastname):
                updated |= profile.set_profile(JBoxUserProfile.ATTR_LAST_NAME, lastname, 'github')

        client_ip = self.get_client_ip()
        if profile.can_set(JBoxUserProfile.ATTR_IP, client_ip):
            updated |= profile.set_profile(JBoxUserProfile.ATTR_IP, client_ip, 'http')

        if updated:
            GitHubAuthHandler.log_debug("updating ip=%r and profile=%r", client_ip, user_info)
            profile.save()