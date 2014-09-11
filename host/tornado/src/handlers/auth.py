import base64, datetime, isodate, json, traceback

import pytz
import tornado
from tornado.auth import GoogleOAuth2Mixin

from jbox_handler import JBoxHandler
from db.user_v2 import JBoxUserV2
from jbox_util import esc_sessname, log_info
from jbox_crypto import signstr

class AuthHandler(JBoxHandler, GoogleOAuth2Mixin):
    AUTH_COOKIE = 'juliabox'
    AUTH_VALID_DAYS = 30
    AUTH_VALID_SECS = (AUTH_VALID_DAYS * 24 * 60 * 60)
    CRED_STORE = {}
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        if self.config("gauth"):
            #self_redirect_uri should be similar to  'http://<host>/hostlaunchipnb/'
            self_redirect_uri = self.request.full_url()
            idx = self_redirect_uri.index("hostlaunchipnb/")
            self_redirect_uri = self_redirect_uri[0:(idx + len("hostlaunchipnb/"))]
            
            # state indicates the stage of auth during multistate auth
            state = self.get_argument('state', None)
                
            code = self.get_argument('code', False)            
            if code != False:
                user = yield self.get_authenticated_user(redirect_uri=self_redirect_uri, code=code)

                # get user info
                http = tornado.httpclient.AsyncHTTPClient()
                auth_string = "%s %s" % (user['token_type'], user['access_token'])
                response = yield http.fetch('https://www.googleapis.com/userinfo/v2/me', headers={"Authorization": auth_string})
                user_info = json.loads(response.body)

                user_id = user_info['email']
                sessname = esc_sessname(user_id)

                jbuser = JBoxUserV2(user_id, create=True)
                if state == 'store_creds':
                    creds = self.make_credentials(user)
                    jbuser.set_gtok(base64.b64encode(creds.to_json()))
                    jbuser.save()
                    #log_info(str(user))
                    #log_info(creds.to_json())
                else:
                    if self.get_cookie("is_invite", "no") == "yes":
                        code, status = jbuser.get_activation_state()
                        if status != JBoxUserV2.ACTIVATION_GRANTED:
                            jbuser.set_activation_state(code, JBoxUserV2.ACTIVATION_REQUESTED)
                            jbuser.save()
                        self.redirect('/?_msg=' + str(status))
                        return
                    else:
                        self.set_session_cookie(user_id)
                        if jbuser.is_new:
                            jbuser.save()
                    self.redirect('/')
                    return
            else:
                if state == 'ask_gdrive':
                    jbox_cookie = AuthHandler.get_session_cookie(self)
                    scope = ['https://www.googleapis.com/auth/drive']
                    extra_params={'approval_prompt': 'force', 'access_type': 'offline', 'login_hint': jbox_cookie['u'], 'include_granted_scopes': 'true', 'state': 'store_creds'}
                else:
                    scope = ['profile', 'email']
                    extra_params={'approval_prompt': 'auto'}
                
                yield self.authorize_redirect(redirect_uri=self_redirect_uri,
                                client_id=self.settings['google_oauth']['key'],
                                scope=scope,
                                response_type='code',
                                extra_params=extra_params)
        else:
            sessname = unquote(self.get_argument("sessname"))
            self.set_session_cookie(sessname)
            self.redirect('/')
        

    def make_credentials(self, user):
        #return AccessTokenCredentials(user['access_token'], "juliabox")
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(user['expires_in']))
        id_token = _extract_id_token(user['id_token'])
        credential = OAuth2Credentials(
            access_token = user['access_token'],
            client_id = self.settings['google_oauth']['key'],
            client_secret = self.settings['google_oauth']['secret'],
            refresh_token = user['refresh_token'],
            token_expiry = token_expiry,
            token_uri = GOOGLE_TOKEN_URI,
            user_agent = None,
            revoke_uri = GOOGLE_REVOKE_URI,
            id_token = id_token,
            token_response = user)
        return credential

    def set_session_cookie(self, user_id):
        t = datetime.datetime.now(pytz.utc).isoformat()
        sign = signstr(user_id + t, self.config('sesskey'))
        
        jbox_cookie = { 'u': user_id, 't': t, 'x': sign }
        self.set_cookie(AuthHandler.AUTH_COOKIE, base64.b64encode(json.dumps(jbox_cookie)))
 
    @staticmethod
    def get_session_cookie(req):
        try:
            jbox_cookie = req.get_cookie(AuthHandler.AUTH_COOKIE)
            if jbox_cookie == None:
                return None
            jbox_cookie = json.loads(base64.b64decode(jbox_cookie))
            sign = signstr(jbox_cookie['u'] + jbox_cookie['t'], AuthHandler._config['sesskey'])
            if sign != jbox_cookie['x']:
                log_info("signature mismatch for " + jbox_cookie['u'])
                return None
    
            d = isodate.parse_datetime(jbox_cookie['t'])
            age = (datetime.datetime.now(pytz.utc) - d).total_seconds()
            if age > AuthHandler.AUTH_VALID_SECS:
                log_info("cookie older than allowed days: " + jbox_cookie['t'])
                return None
            return jbox_cookie
        except:
            log_info("exception while reading cookie")
            traceback.print_exc()
            return None
 
    @staticmethod
    def fetch_auth_results(req):
        try:
            jbox_cookie = req.get_cookie(AuthHandler.AUTH_COOKIE)
            if jbox_cookie == None:
                return None
            jbox_cookie = json.loads(base64.b64decode(jbox_cookie))
            sign = signstr(jbox_cookie['s'] + jbox_cookie['t'], AuthHandler._config['sesskey'])
            if sign != jbox_cookie['x']:
                log_info("signature mismatch for " + jbox_cookie['s'])
    
            d = isodate.parse_datetime(jbox_cookie['t'])
            age = (datetime.datetime.now(pytz.utc) - d).total_seconds()
            if age > AuthHandler.AUTH_VALID_SECS:
                log_info("cookie older than allowed days: " + jbox_cookie['t'])
                return None
            
            jbox_cookie['creds'] = AuthHandler.CRED_STORE[jbox_cookie['s']].to_json()
            return jbox_cookie
        except:
            log_info("exception while converting cookie to auth results")
            traceback.print_exc()
            return None
