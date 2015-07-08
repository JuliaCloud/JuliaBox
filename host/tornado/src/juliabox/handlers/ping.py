import tornado
import tornado.web
import tornado.gen

from handler_base import JBoxHandler
from juliabox.jbox_container import JBoxContainer


class PingHandler(JBoxHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        valid_req = self.is_valid_req()
        sessname = self.get_session_id(validate=False)
        if valid_req:
            JBoxContainer.record_ping("/" + sessname)
            self.set_status(status_code=204)
            self.finish()
        else:
            self.log_warn("Invalid ping request for " + sessname)
            self.send_error(status_code=403)