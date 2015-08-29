__author__ = 'tan'
import time
import zmq
from datetime import timedelta
from zmq.devices.basedevice import ThreadDevice

from juliabox.db import JBoxAPISpec
from juliabox.jbox_util import LoggerMixin
from juliabox.cloud import Compute


class APIQueue(LoggerMixin):
    BUFFER_SZ = 20
    QUEUES = dict()
    QLEN_WT = 0.25
    QUEUE_CACHE = []

    def __init__(self, api_name):
        self.cmd = self.image_name = self.api_name = None
        self.num_outstanding = self.mean_outstanding = self.timeout = 0

        self.reset(api_name)
        self.qdev = qdev = ThreadDevice(zmq.QUEUE, zmq.XREP, zmq.XREQ)

        endpt_in, endpt_out = APIQueue.allocate_random_endpoints()
        self.endpoints = endpt_in, endpt_out

        qdev.bind_in(endpt_in)
        qdev.bind_out(endpt_out)

        if APIQueue._zmq_major_ver() > 2:
            qdev.setsockopt_in(zmq.SNDHWM, APIQueue.BUFFER_SZ)
            qdev.setsockopt_out(zmq.RCVHWM, APIQueue.BUFFER_SZ)
            qdev.setsockopt_in(zmq.RCVHWM, APIQueue.BUFFER_SZ)
            qdev.setsockopt_out(zmq.SNDHWM, APIQueue.BUFFER_SZ)
        else:
            qdev.setsockopt_in(zmq.HWM, APIQueue.BUFFER_SZ)
            qdev.setsockopt_out(zmq.HWM, APIQueue.BUFFER_SZ)
        qdev.start()

        APIQueue.QUEUES[api_name] = self
        self.log_debug("Created " + self.debug_str())

    def reset(self, api_name):
        self.api_name = api_name
        self.num_outstanding = 0
        self.mean_outstanding = 0

        spec = JBoxAPISpec(api_name)
        timeout_secs = spec.get_timeout_secs()
        self.timeout = timedelta(seconds=timeout_secs) if timeout_secs is not None else None

        self.cmd = spec.get_cmd()
        self.image_name = spec.get_image_name()

    @staticmethod
    def _zmq_major_ver():
        return int(zmq.zmq_version()[0])

    def debug_str(self):
        return "APIQueue %s (%s, %s). outstanding: %g, %g" % (self.api_name, self.get_endpoint_in(),
                                                              self.get_endpoint_out(), self.num_outstanding,
                                                              self.mean_outstanding)

    def get_endpoint_in(self):
        return self.endpoints[0]

    def get_endpoint_out(self):
        return self.endpoints[1]

    def get_timeout(self):
        return self.timeout

    def get_command(self):
        return self.cmd

    def get_image_name(self):
        return self.image_name

    @staticmethod
    def release_queue(api_name):
        queue = APIQueue.get_queue(api_name, alloc=False)
        if queue is None:
            return
        del APIQueue.QUEUES[api_name]
        APIQueue.QUEUE_CACHE.append(queue)
        APIQueue.log_debug("Released (cached) queue: %s", queue.debug_str())

    @staticmethod
    def get_queue(api_name, alloc=True):
        if api_name in APIQueue.QUEUES:
            return APIQueue.QUEUES[api_name]
        elif alloc:
            if len(APIQueue.QUEUE_CACHE) > 0:
                queue = APIQueue.QUEUE_CACHE.pop()
                queue.reset(api_name)
                APIQueue.QUEUES[api_name] = queue
                APIQueue.log_debug("Created (reused) queue: %s", queue.debug_str())
            else:
                queue = APIQueue(api_name)
                APIQueue.log_debug("Created queue: %s", queue.debug_str())
            return queue
        return None

    @staticmethod
    def allocate_random_endpoints():
        ctx = zmq.Context.instance()
        binder = ctx.socket(zmq.REQ)

        bind_pfx = "tcp://" + Compute.get_docker_bridge_ip()
        port_in = binder.bind_to_random_port(bind_pfx)
        port_out = binder.bind_to_random_port(bind_pfx)
        binder.close()
        time.sleep(0.25)

        endpoint_in = bind_pfx + str(':') + str(port_in)
        endpoint_out = bind_pfx + str(':') + str(port_out)

        return endpoint_in, endpoint_out

    def incr_outstanding(self, num):
        self.num_outstanding += num
        self.mean_outstanding = (APIQueue.QLEN_WT * self.mean_outstanding + self.num_outstanding) / (1+APIQueue.QLEN_WT)
