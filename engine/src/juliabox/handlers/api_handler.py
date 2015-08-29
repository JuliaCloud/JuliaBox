__author__ = 'tan'
import tornado.web
import tornado.httputil
import json
import struct

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

    @staticmethod
    def pack_into_binary(data):
        packed = str()
        for d in data:
            packed += struct.pack('B', d)
        return packed

    def on_recv(self, msg):
        self.log_info("response received for %s", self.request.uri)
        if 'nid' in msg:
            APIContainer.record_ping(msg['nid'])
        code = msg.get('code', 500)
        if code == 200:
            start_line = tornado.httputil.ResponseStartLine('', self._status_code, self._reason)
            hdrs = tornado.httputil.HTTPHeaders(msg.get('hdrs', {}))
            data = msg['data']

            if type(data) == list:
                hdrs.add("Content-Length", str(len(data)))
                data = APIHandler.pack_into_binary(data)
            elif type(data) == dict:
                data = json.dumps(data)
            else:
                data = str(data)

            self.request.connection.write_headers(start_line, hdrs, data)
            self.request.connection.finish()
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