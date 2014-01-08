#! /usr/bin/env python

from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from dock import *

import tornado.ioloop
import tornado.web
import tornado.auth
import random
import string
import hashlib
import hmac
import base64
import os.path


f = open("conf/tornado.conf")
cfg = eval(f.read())
f.close()

if os.path.isfile("conf/tornado.user"):
    f = open("conf/tornado.user")
    ucfg = eval(f.read())
    f.close()
    
    cfg.update(ucfg)


def esc_sessname(s):
    return s.replace("@", "_at_").replace(".", "_")

cfg["admin_sessnames"]=[]
for ad in cfg["admin_users"]:
    cfg["admin_sessnames"].append(esc_sessname(ad))

cfg["protected_docknames"]=[]
for ps in cfg["protected_sessions"]:
    cfg["protected_docknames"].append("/" + esc_sessname(ps))

def signstr(s, k):
    h=hmac.new(k, s, hashlib.sha1)
    return base64.b64encode(h.digest())

def rendertpl(rqst, tpl, **kwargs):
    rqst.render("../www/" + tpl, **kwargs)


def launch_docker(rqst, sessname, clear=True):
    is_active_container, c = is_container(sessname, all=False)
        
    if (get_num_active_containers() > cfg["numlocalmax"]) and (not is_active_container) :
        rendertpl(rqst, "index.tpl", cfg=cfg, err="Maximum number of containers active. Please try after sometime.")
    else:
        instid, uplport, ipnbport = launch_container(sessname, clear, c)
        rqst.set_cookie("sessname", sessname)
        rqst.set_cookie("hostupl", str(uplport))
        rqst.set_cookie("hostipnb", str(ipnbport))
        sign = signstr(sessname + str(uplport) + str(ipnbport), cfg["sesskey"])
        
        rqst.set_cookie("sign", sign)
        rendertpl(rqst, "ipnbsess.tpl")
    



class MainHandler(tornado.web.RequestHandler):
    def get(self):
        rendertpl(self, "index.tpl", cfg=cfg, err='')

def is_clear_sess_set(rqst):
    clear_old_sess = rqst.get_argument("clear_old_sess", False)
    if clear_old_sess != False:
        clear_old_sess = True
    
    return clear_old_sess
    
def unquote(s):
    s = s.strip()
    if s[0] == '"':
        return s[1:-1]
    else:
        return s


class LaunchDocker(tornado.web.RequestHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        terminate_expired_containers(cfg)
        
        if cfg["gauth"]:
            if self.get_argument("openid.mode", None):
                user = yield self.get_authenticated_user()
                sessname = esc_sessname(user['email'])
                launch_docker(self, sessname, is_clear_sess_set(self)) 

            else:
                yield self.authenticate_redirect(callback_uri = self.request.uri)
                
        else:
            sessname = unquote(self.get_argument("sessname"))
            launch_docker(self, sessname, is_clear_sess_set(self)) 
        


class AdminHandler(tornado.web.RequestHandler):
    def get(self):
        terminate_expired_containers(cfg)
        sessname = unquote(self.get_cookie("sessname"))
        dockname = "/" + sessname
        delete = {}
        delete_id = self.get_argument("delete_id", '')
        admin_user = (sessname in cfg["admin_sessnames"]) or (cfg["admin_sessnames"] == [])

        for k in ["delete_all_inactive", "delete_all"]:
            if self.get_argument(k, None) != None :
                delete[k] = True
            else:
                delete[k] = False

        if len(sessname) == 0:
            self.send_error()


        iac = []
        ac = []
        sections = []
        
        if admin_user:
            jsonobj = dckr.containers(all=all)
            
            if delete["delete_all_inactive"] or delete["delete_all"] :
                for c in jsonobj:
                    if (not (dockname == c[u"Names"][0])) and (not (c[u"Names"][0] in cfg["protected_docknames"])) :
                        if delete["delete_all"] or (c["Ports"] == None):
                            dckr.kill(c[u"Id"])
                            dckr.remove_container(c[u"Id"])
                            
            elif not (delete_id == ''):
                dckr.kill(delete_id)
                dckr.remove_container(delete_id)

            # get them all again (in case we deleted some)
            jsonobj = dckr.containers(all=all)
            for c in jsonobj:
                o = {}
                o["Id"] = c["Id"][0:12]
                o["Status"] = c["Status"]
                o["Name"] = c["Names"][0]
                
                if (c["Ports"] == None):
                    iac.append(o)
                else:
                    ac.append(o)
                    
            sections = [["Active", ac], ["Inactive", iac]]        


        rendertpl(self, "ipnbadmin.tpl", d={"admin_user" : admin_user,
                                        "sessname" : sessname, 
                                        "sections" : sections
                                        }, cfg=cfg)


if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/hostlaunchipnb/", LaunchDocker),
        (r"/hostadmin/", AdminHandler)
    ])
    application.settings["cookie_secret"] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    application.listen(cfg["port"])
    tornado.ioloop.IOLoop.instance().start()
    
    
