import tornado

from jbox_util import log_info, esc_sessname, read_config
from jbox_crypto import signstr
from jbox_handler import JBoxHandler
from jbox_container import JBoxContainer

cfg = read_config()

def is_valid_req(req):
    sessname = req.get_cookie("sessname")
    if None == sessname:
        return False
    sessname  = sessname.replace('"', '')
    hostshell = req.get_cookie("hostshell").replace('"', '')
    hostupl   = req.get_cookie("hostupload").replace('"', '')
    hostipnb  = req.get_cookie("hostipnb").replace('"', '')
    signval   = req.get_cookie("sign").replace('"', '')
    
    sign = signstr(sessname + hostshell + hostupl + hostipnb, cfg["sesskey"])
    if (sign != signval):
        log_info('not valid req. signature not matching')
        return False
    if not JBoxContainer.is_valid_container("/" + sessname, (hostshell, hostupl, hostipnb)):
        log_info('not valid req. container deleted or ports not matching')
        return False
    return True

class PingHandler(JBoxHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        sessname = str(self.get_cookie("sessname")).replace('"', '')
        if is_valid_req(self):
            JBoxContainer.record_ping("/" + esc_sessname(sessname))
            self.set_status(status_code=204)
            self.finish()
        else:
            log_info("Invalid ping request for " + sessname)
            self.send_error(status_code=403)

