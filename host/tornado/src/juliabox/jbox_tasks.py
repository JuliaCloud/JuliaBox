import zmq
import json

from jbox_util import LoggerMixin, JBoxCfg
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
    CMD_UPDATE_DISK_STATES = 7
    CMD_TERMINATE_OR_DELETE_CLUSTER = 8

    CMD_REQ_RESP = 50
    CMD_SESSION_STATUS = 51

    ENCKEY = None
    PORTS = None

    SINGLETON_INSTANCE = None

    def __init__(self, ports, mode):
        self._mode = mode
        self._ctx = zmq.Context()

        ppmode = zmq.PUSH if (mode == JBoxAsyncJob.MODE_PUB) else zmq.PULL
        self._push_pull_sock = self._ctx.socket(ppmode)

        rrmode = zmq.REQ if (mode == JBoxAsyncJob.MODE_PUB) else zmq.REP

        local_ip = CloudHost.instance_local_ip()
        JBoxAsyncJob.log_debug("local hostname [%s]", local_ip)

        ppbindaddr = 'tcp://%s:%d' % (local_ip, ports[0],)
        ppconnaddr = 'tcp://%s:%d' % (local_ip, ports[0],)
        rraddr = 'tcp://%s:%d' % (local_ip, ports[1],)
        self._rrport = ports[1]
        self._poller = zmq.Poller()

        if mode == JBoxAsyncJob.MODE_PUB:
            self._push_pull_sock.bind(ppbindaddr)
        else:
            self._push_pull_sock.connect(ppconnaddr)
            self._poller.register(self._push_pull_sock, zmq.POLLIN)
            self._req_rep_sock = self._ctx.socket(rrmode)
            self._req_rep_sock.bind(rraddr)

    @staticmethod
    def configure():
        JBoxAsyncJob.PORTS = JBoxCfg.get('async_job_ports')
        JBoxAsyncJob.ENCKEY = JBoxCfg.get('sesskey')

    @staticmethod
    def init(async_mode):
        JBoxAsyncJob.SINGLETON_INSTANCE = JBoxAsyncJob(JBoxAsyncJob.PORTS, async_mode)

    @staticmethod
    def get():
        return JBoxAsyncJob.SINGLETON_INSTANCE

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
        else:
            dest = CloudHost.instance_local_ip(dest)
        if port is None:
            port = self._rrport
        rraddr = 'tcp://%s:%d' % (dest, port)

        JBoxAsyncJob.log_debug("sendrecv to %s. connecting...", rraddr)
        sock = self._ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.LINGER, 5*1000)
        sock.connect(rraddr)

        poller = zmq.Poller()
        poller.register(sock, zmq.POLLOUT)

        if poller.poll(10*1000):
            sock.send_json(self._make_msg(cmd, data))
        else:
            sock.close()
            raise IOError("could not connect to %s", rraddr)

        poller.modify(sock, zmq.POLLIN)
        if poller.poll(10*1000):
            msg = sock.recv_json()
        else:
            sock.close()
            raise IOError("did not receive anything from %s", rraddr)

        JBoxAsyncJob.log_debug("sendrecv to %s. received.", rraddr)
        sock.close()
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

    @staticmethod
    def async_refresh_disks():
        JBoxAsyncJob.log_info("scheduling refresh of loopback disks")
        JBoxAsyncJob.get().send(JBoxAsyncJob.CMD_REFRESH_DISKS, '')

    @staticmethod
    def async_update_user_home_image():
        JBoxAsyncJob.log_info("scheduling update of user home image")
        JBoxAsyncJob.get().send(JBoxAsyncJob.CMD_UPDATE_USER_HOME_IMAGE, '')

    @staticmethod
    def async_collect_stats():
        JBoxAsyncJob.log_info("scheduling stats collection")
        JBoxAsyncJob.get().send(JBoxAsyncJob.CMD_COLLECT_STATS, '')

    @staticmethod
    def async_update_disk_state():
        JBoxAsyncJob.log_info("updating disk states")
        JBoxAsyncJob.get().send(JBoxAsyncJob.CMD_UPDATE_DISK_STATES, '')

    @staticmethod
    def async_schedule_activations():
        JBoxAsyncJob.log_info("scheduling activations")
        JBoxAsyncJob.get().send(JBoxAsyncJob.CMD_AUTO_ACTIVATE, '')

    @staticmethod
    def async_launch_by_name(name, email, reuse=True):
        JBoxAsyncJob.log_info("Scheduling startup name:%s email:%s", name, email)
        JBoxAsyncJob.get().send(JBoxAsyncJob.CMD_LAUNCH_SESSION, (name, email, reuse))

    @staticmethod
    def async_backup_and_cleanup(dockid):
        JBoxAsyncJob.log_info("scheduling cleanup for %s", dockid)
        JBoxAsyncJob.get().send(JBoxAsyncJob.CMD_BACKUP_CLEANUP, dockid)

    @staticmethod
    def sync_session_status(instance_id):
        JBoxAsyncJob.log_debug("fetching session status from %s", instance_id)
        return JBoxAsyncJob.get().sendrecv(JBoxAsyncJob.CMD_SESSION_STATUS, {}, dest=instance_id)

    @staticmethod
    def async_terminate_or_delete_cluster(cluster_id):
        JBoxAsyncJob.log_info("scheduling termination or deletion of %s", cluster_id)
        JBoxAsyncJob.get().send(JBoxAsyncJob.CMD_TERMINATE_OR_DELETE_CLUSTER, cluster_id)