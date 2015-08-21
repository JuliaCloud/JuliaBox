__author__ = 'tan'
import zmq
import json
from zmq.eventloop import ioloop, zmqstream

from juliabox.jbox_util import LoggerMixin
from api_queue import APIQueue


class APIConnector(LoggerMixin):
    CONNS = dict()
    MAX_CONNS = 2
    CMD_TERMINATE = ":terminate"

    def __init__(self, api_name):
        self.queue = APIQueue.get_queue(api_name)
        ctx = zmq.Context.instance()
        self.api_name = api_name
        self.sock = ctx.socket(zmq.REQ)
        self.sock.connect(self.queue.get_endpoint_in())
        self.has_errors = False
        self.timeout_callback = None
        self.timeout = self.queue.get_timeout()

        if api_name in APIConnector.CONNS:
            APIConnector.CONNS[api_name].append(self)
        else:
            APIConnector.CONNS[api_name] = [self]

        self.log_debug("%s: created", self.debug_str())

    def debug_str(self):
        return "APIConnector %s. dflt timeout:%s" % (self.api_name, str(self.timeout))

    @staticmethod
    def release_connectors(api_name):
        if api_name in APIConnector.CONNS:
            APIConnector.log_debug("releasing all %s connectors", api_name)
            del APIConnector.CONNS[api_name]
        else:
            APIConnector.log_debug("already release all %s connectors", api_name)

    @staticmethod
    def _get_conn(api_name):
        if not ((api_name in APIConnector.CONNS) and (len(APIConnector.CONNS[api_name]) > 0)):
            APIConnector(api_name)
        return APIConnector.CONNS[api_name].pop()

    def _release(self):
        self.queue.incr_outstanding(-1)
        if self.api_name in APIConnector.CONNS:
            cache = APIConnector.CONNS[self.api_name]
            if not self.has_errors and (len(cache) < APIConnector.MAX_CONNS):
                cache.append(self)

    def conn_send_recv(self, send_data, on_recv, on_timeout, timeout=None):
        stream = zmqstream.ZMQStream(self.sock)
        loop = ioloop.IOLoop.instance()
        if timeout is None:
            timeout = self.timeout

        def _on_timeout():
            APIConnector.log_debug("%s: timed out", self.debug_str())
            self.has_errors = True
            self.timeout_callback = None
            stream.stop_on_recv()
            stream.close()
            self._release()
            if on_timeout is not None:
                on_timeout()

        def _on_recv(msg):
            APIConnector.log_debug("%s: message received", self.debug_str())
            if self.timeout_callback is not None:
                loop.remove_timeout(self.timeout_callback)
                self.timeout_callback = None
            stream.stop_on_recv()
            self._release()
            msg = json.loads(msg[0])
            if on_recv is not None:
                on_recv(msg)

        self.log_debug("%s: making call with timeout %r", self.debug_str(), timeout)
        self.timeout_callback = loop.add_timeout(timeout, _on_timeout)
        stream.on_recv(_on_recv)
        self.queue.incr_outstanding(1)
        self.sock.send(send_data)

    @staticmethod
    def send_recv(api_name, cmd, args=None, vargs=None, on_recv=None, on_timeout=None, on_overload=None, timeout=None):
        send_data = APIConnector.make_req(cmd, args=args, vargs=vargs)
        api = APIConnector._get_conn(api_name)

        if api.queue.mean_outstanding >= APIQueue.BUFFER_SZ:
            on_overload()
            return

        APIConnector.log_debug("%s: calling %s", api.debug_str(), cmd)
        api.conn_send_recv(send_data, on_recv, on_timeout, timeout)

    @staticmethod
    def send_terminate_msg(api_name, on_recv=None):
        APIConnector.send_recv(api_name, APIConnector.CMD_TERMINATE, on_recv=on_recv)

    @staticmethod
    def make_req(cmd, args=None, vargs=None):
        req = {'cmd': cmd}
        if (args is not None) and (len(args) > 0):
            req['args'] = args
        if (vargs is not None) and (len(vargs) > 0):
            req['vargs'] = vargs

        return json.dumps(req)