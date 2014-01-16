#! /usr/bin/env python

from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from jdockutil import *

import tornado.ioloop
import tornado.web
import tornado.auth
import random
import string
import hashlib
import hmac
import base64
import os.path
import sys
import calendar
import time
import sys


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
                    if ("Names" not in c) or (c["Names"] == None):
                        kill_and_remove(c)
                        
                    elif (dockname != c[u"Names"][0]) and (c[u"Names"][0] not in cfg["protected_docknames"]) :
                        if delete["delete_all"] or (c["Ports"] == None):
                            kill_and_remove(c)
                            
            elif not (delete_id == ''):
                kill_and_remove_id(delete_id)

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
                
                if (c["Ports"] == None):
                    iac.append(o)
                else:
                    ac.append(o)
                    
            sections = [["Active", ac], ["Inactive", iac]]        


        rendertpl(self, "ipnbadmin.tpl", d={"admin_user" : admin_user,
                                        "sessname" : sessname, 
                                        "sections" : sections
                                        }, cfg=cfg)



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
            self.send_error(status_code=403)
        else:
            map_dockname_ping["/" + esc_sessname(sessname)] = calendar.timegm(time.gmtime())
            self.set_status(status_code=204)
            self.finish()



def do_housekeeping():
    terminate_expired_containers()
    
    

if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/hostlaunchipnb/", LaunchDocker),
        (r"/hostadmin/", AdminHandler),
        (r"/ping/", PingHandler)
    ])
    application.settings["cookie_secret"] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    application.listen(cfg["port"])
    
    record_active_containers()
    terminate_expired_containers()

    ioloop = tornado.ioloop.IOLoop.instance()
    ct = tornado.ioloop.PeriodicCallback(do_housekeeping, 60000, ioloop)
    ct.start()
    
    ioloop.start()
    
    
