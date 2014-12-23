import zmq
import json
from jbox_util import LoggerMixin
from jbox_crypto import signstr
from cloud.aws import CloudHost


class JBoxAsyncJob(LoggerMixin):
    MODE_PUB = 0
    MODE_SUB = 1

    CMD_BACKUP_CLEANUP = 1
    CMD_LAUNCH_SESSION = 2
    CMD_AUTO_ACTIVATE = 3
    CMD_UPDATE_USER_HOME_IMAGE = 4
    CMD_REFRESH_DISKS = 5
    CMD_COLLECT_STATS = 6

    CMD_REQ_RESP = 50
    CMD_SESSION_STATUS = 51

    ENCKEY = None

    def __init__(self, ports, mode):
        self._mode = mode
        self._ctx = zmq.Context()

        ppmode = zmq.PUSH if (mode == JBoxAsyncJob.MODE_PUB) else zmq.PULL
        self._push_pull_sock = self._ctx.socket(ppmode)

        rrmode = zmq.REQ if (mode == JBoxAsyncJob.MODE_PUB) else zmq.REP
        self._req_rep_sock = self._ctx.socket(rrmode)

        #public_hostname = CloudHost.instance_public_hostname()
        #if public_hostname == 'localhost':
        #    public_hostname = '127.0.0.1'

        ppbindaddr = 'tcp://*:%d' % (ports[0],)
        ppconnaddr = 'tcp://127.0.0.1:%d' % (ports[0],)
        rraddr = 'tcp://*:%d' % (ports[1],)
        self._rrport = ports[1]
        self._poller = zmq.Poller()

        if mode == JBoxAsyncJob.MODE_PUB:
            self._push_pull_sock.bind(ppbindaddr)
            self._req_rep_sock.setsockopt(zmq.LINGER, 0)
        else:
            self._push_pull_sock.connect(ppconnaddr)
            self._poller.register(self._push_pull_sock, zmq.POLLIN)
            self._req_rep_sock.bind(rraddr)

    @staticmethod
    def configure(cfg):
        JBoxAsyncJob.ENCKEY = cfg['sesskey']

    @staticmethod
    def _make_msg(cmd, data):
        srep = json.dumps([cmd, data])
        sign = signstr(srep, JBoxAsyncJob.ENCKEY)
        msg = {
            'cmd': cmd,
            'data': data,
            'sign': sign
        }
        return msg

    @staticmethod
    def _extract_msg(msg):
        srep = json.dumps([msg['cmd'], msg['data']])
        sign = signstr(srep, JBoxAsyncJob.ENCKEY)
        if sign == msg['sign']:
            return msg['cmd'], msg['data']
        JBoxAsyncJob.log_error("signature mismatch. expected [%s], got [%s], srep [%s]", sign, msg['sign'], srep)
        raise ValueError("invalid signature for cmd: %s, data: %s" % (msg['cmd'], msg['data']))

    def sendrecv(self, cmd, data, dest=None, port=None):
        if (dest is None) or (dest == 'localhost'):
            dest = '127.0.0.1'
        if port is None:
            port = self._rrport
        rraddr = 'tcp://%s:%d' % (dest, port)

        JBoxAsyncJob.log_debug("sendrecv to %s. connecting...", rraddr)
        self._req_rep_sock.connect(rraddr)

        poller = zmq.Poller()
        poller.register(self._req_rep_sock, zmq.POLLOUT)

        if poller.poll(10*1000):
            self._req_rep_sock.send_json(self._make_msg(cmd, data))
        else:
            raise IOError("could not connect to %s", rraddr)

        poller.modify(self._req_rep_sock, zmq.POLLIN)
        if poller.poll(10*1000):
            msg = self._req_rep_sock.recv_json()
        else:
            raise IOError("did not receive anything from %s", rraddr)

        JBoxAsyncJob.log_debug("sendrecv to %s. received.", rraddr)
        #self._req_rep_sock.close()
        return msg

    def respond(self, callback):
        msg = self._req_rep_sock.recv_json()
        cmd, data = self._extract_msg(msg)
        resp = callback(cmd, data)
        self._req_rep_sock.send_json(resp)

    def send(self, cmd, data):
        assert self._mode == JBoxAsyncJob.MODE_PUB
        self._push_pull_sock.send_json(self._make_msg(cmd, data))

    def recv(self):
        msg = self._push_pull_sock.recv_json()
        return self._extract_msg(msg)

    def poll(self, req_resp_pending=False):
        if not req_resp_pending:
            self._poller.register(self._req_rep_sock, zmq.POLLIN)
        else:
            if self._req_rep_sock in self._poller.sockets:
                self._poller.unregister(self._req_rep_sock)

        socks = dict(self._poller.poll())
        ppreq = (self._push_pull_sock in socks) and (socks[self._push_pull_sock] == zmq.POLLIN)
        rrreq = (self._req_rep_sock in socks) and (socks[self._req_rep_sock] == zmq.POLLIN)

        return ppreq, rrreq