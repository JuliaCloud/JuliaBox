__author__ = 'tan'
import tornado.web
import json

from handler_base import JBoxHandler
from juliabox.api import APIContainer, APIConnector


class APIHandler(JBoxHandler):
    def get(self):
        self.log_debug("API server handler got GET request")
        return self.post()

    @tornado.web.asynchronous
    def post(self):
        self.log_debug("API server handler got POST request")
        uri = self.request.uri
        self.log_debug("called with uri: %s", uri)

        comps = filter(bool, uri.split('/'))
        if len(comps) < 2:
            self.send_error(status_code=404)
            return

        api_name = comps[0]
        cmd = comps[1]
        args = comps[2:]
        vargs = self.request.arguments

        self.log_debug("calling service:%s. cmd:%s. nargs: %d. nvargs: %d", api_name, cmd, len(args), len(vargs))
        APIContainer.ensure_container_available(api_name)
        APIConnector.send_recv(api_name, cmd, args=args, vargs=vargs,
                               on_recv=self.on_recv,
                               on_timeout=self.on_timeout,
                               on_overload=self.on_overload)

    def on_recv(self, msg):
        self.log_info("response for %s: [%r] [%s]", self.request.uri, msg, str(msg))
        if 'nid' in msg:
            APIContainer.record_ping(msg['nid'])
        code = msg.get('code', 500)
        if code == 200:
            hdrs = msg.get('hdrs', {})
            for (hdr_n, hdr_v) in hdrs.iteritems():
                self.set_header(hdr_n, hdr_v)
            self.write(json.dumps(msg['data']))
            self.finish()
        else:
            self.send_error(status_code=code)

    def on_overload(self):
        self.log_error("server overloaded %s", self.request.uri)
        self.send_error(status_code=503)

    def on_timeout(self):
        self.log_error("timed out serving %s", self.request.uri)
        self.send_error(status_code=408)
    #
    # def is_valid_api(self, api_name):
    #     return api_name in self.config("api_names", [])