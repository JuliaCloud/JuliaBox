#! /usr/bin/env python

from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from jdockutil import *

import tornado.ioloop, tornado.web, tornado.auth
import base64, hashlib, hmac, json, os, os.path, random, string, sys, time


def signstr(s, k):
    h = hmac.new(k, s, hashlib.sha1)
    return base64.b64encode(h.digest())
 
def unquote(s):
    s = s.strip()
    if s[0] == '"':
        return s[1:-1]
    else:
        return s

def rendertpl(rqst, tpl, **kwargs):
    rqst.render("../www/" + tpl, **kwargs)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        rendertpl(self, "index.tpl", cfg=cfg, err='')


class LaunchDocker(tornado.web.RequestHandler, tornado.auth.GoogleOAuth2Mixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        if cfg["gauth"]:
            #self_redirect_uri should be similar to  'http://<host>/hostlaunchipnb/'
            self_redirect_uri = self.request.full_url()
            idx = self_redirect_uri.index("hostlaunchipnb/")
            self_redirect_uri = self_redirect_uri[0:(idx + len("hostlaunchipnb/"))]
            if self.get_argument('code', False):
                user = yield self.get_authenticated_user(redirect_uri=self_redirect_uri, code=self.get_argument('code'))
                #log_info(str(user))

                # get user info
                http = tornado.httpclient.AsyncHTTPClient()
                auth_string = "%s %s" % (user['token_type'], user['access_token'])
                response = yield http.fetch('https://www.googleapis.com/userinfo/v2/me', headers={"Authorization": auth_string})
                user = json.loads(response.body)

                #log_info(str(user))
                sessname = esc_sessname(user['email'])
                self.chk_and_launch_docker(sessname, self.can_reuse_session())
            else:
                yield self.authorize_redirect(redirect_uri=self_redirect_uri,
                                client_id=self.settings['google_oauth']['key'],
                                scope=['profile', 'email'],
                                response_type='code',
                                extra_params={'approval_prompt': 'auto'})
        else:
            sessname = unquote(self.get_argument("sessname"))
            self.chk_and_launch_docker(sessname, self.can_reuse_session())

    def can_reuse_session(self):
        clear_old_sess = self.get_argument("clear_old_sess", False)
        if clear_old_sess != False:
            clear_old_sess = True
        
        return (not clear_old_sess)

    def chk_and_launch_docker(self, sessname, reuse=True):
        cont = JDockContainer.get_by_name(sessname)

        if (None != cont) and (not cont.is_running()) and (JDockContainer.num_active() > cfg['numlocalmax']):
            rendertpl(self, "index.tpl", cfg=cfg, err="Maximum number of containers active. Please try after sometime.")
        else:
            cont = JDockContainer.launch_by_name(sessname, reuse)
            (uplport, ipnbport) = cont.get_host_ports()
            sign = signstr(sessname + str(uplport) + str(ipnbport), cfg["sesskey"])
            self.set_cookie("sessname", sessname)
            self.set_cookie("hostupl", str(uplport))
            self.set_cookie("hostipnb", str(ipnbport))
            self.set_cookie("sign", sign)
            rendertpl(self, "ipnbsess.tpl", sessname=sessname, cfg=cfg)


class AdminHandler(tornado.web.RequestHandler):
    def get(self):
        sessname = unquote(self.get_cookie("sessname"))

        if len(sessname) == 0:
            self.send_error()

        dockname = "/" + sessname
        admin_user = (sessname in cfg["admin_sessnames"]) or (cfg["admin_sessnames"] == [])

        delete_id = self.get_argument("delete_id", '')
        stop_id = self.get_argument("stop_id", '')
        stop_all = (self.get_argument('stop_all', None) != None)

        iac = []
        ac = []
        sections = [["Active", ac], ["Inactive", iac]]
        
        cont = JDockContainer.get_by_name(sessname)
        d = {
                "admin_user" : admin_user,
                "sessname" : sessname, 
                "created" : cont.time_created(), 
                "started" : cont.time_started(),
                "sections" : sections
            }

        if admin_user:
            if stop_all:
                all_containers = dckr.containers(all=False)
                for c in all_containers:
                    cont = JDockContainer(c['Id'])
                    cname = cont.get_name()

                    if None == cname:
                        log_info("Admin: Not stopping unknown " + cont.debug_str())
                    elif cname not in cfg["protected_docknames"]:
                        cont.stop()
                            
            elif not (stop_id == ''):
                cont = JDockContainer(stop_id)
                cont.stop()
            elif not (delete_id == ''):
                cont = JDockContainer(stop_id)
                cont.delete()

            # get them all again (in case we deleted some)
            jsonobj = dckr.containers(all=all)
            for c in jsonobj:
                o = {}
                o["Id"] = c["Id"][0:12]
                o["Status"] = c["Status"]
                if ("Names" in c) and (c["Names"] != None): 
                    o["Name"] = c["Names"][0]
                else:
                    o["Name"] = "/None"
                
                if (c["Ports"] == None) or (c["Ports"] == []):
                    iac.append(o)
                else:
                    ac.append(o)

        rendertpl(self, "ipnbadmin.tpl", d=d, cfg=cfg)



class PingHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        #validate the request
        sessname = self.get_cookie("sessname").replace('"', '')
        hostupl = self.get_cookie("hostupl").replace('"', '')
        hostipnb = self.get_cookie("hostipnb").replace('"', '')
        signval = self.get_cookie("sign").replace('"', '')
        
        sign = signstr(sessname + hostupl + hostipnb, cfg["sesskey"])
        if sign != signval:
            log_info("Invalid ping request for " + str(sessname))
            self.send_error(status_code=403)
        else:
            JDockContainer.record_ping("/" + esc_sessname(sessname))
            self.set_status(status_code=204)
            self.finish()


def do_housekeeping():
    JDockContainer.maintain(delete_timeout=cfg['expire'], stop_timeout=cfg['inactivity_timeout'], protected_names=cfg['protected_docknames'])

def do_backups():
    JDockContainer.backup_all()

    

if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/hostlaunchipnb/", LaunchDocker),
        (r"/hostadmin/", AdminHandler),
        (r"/ping/", PingHandler)
    ])
    application.settings["cookie_secret"] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    application.settings["google_oauth"] = cfg["google_oauth"]
    application.listen(cfg["port"])
    
    ioloop = tornado.ioloop.IOLoop.instance()

    # run container maintainence every 10 minutes
    ct = tornado.ioloop.PeriodicCallback(do_housekeeping, 10*60*1000, ioloop)
    ct.start()

    # backup user files every 1 hour
    cbackup = tornado.ioloop.PeriodicCallback(do_backups, 60*60*1000, ioloop)
    cbackup.start()
    
    ioloop.start()


