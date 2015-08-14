__author__ = 'tan'

import socket
import signal

import tornado.web
import tornado.auth
from zmq.eventloop import ioloop

from cloud import Compute
import db
from db import is_cluster_leader
from jbox_tasks import JBoxAsyncJob
from jbox_util import LoggerMixin, JBoxCfg
from api import APIContainer
from handlers import APIHandler, APIInfoHandler


class JBoxAPI(LoggerMixin):
    shutdown = False

    def __init__(self):
        LoggerMixin.configure()
        db.configure()
        Compute.configure()
        APIContainer.configure()

        JBoxAsyncJob.configure()
        JBoxAsyncJob.init(JBoxAsyncJob.MODE_PUB)

        self.application = tornado.web.Application(handlers=[
            (r"^/", APIInfoHandler),
            (r"^/.*/.*", APIHandler)
        ])

        self.application.settings["cookie_secret"] = JBoxCfg.get('sesskey')
        self.application.listen(JBoxCfg.get('api.manager_port'), address=socket.gethostname())
        self.application.listen(JBoxCfg.get('api.manager_port'), address='localhost')

        self.ioloop = ioloop.IOLoop.instance()

        # run container maintainence every 5 minutes
        run_interval = 5 * 60 * 1000
        self.log_info("Container maintenance every " + str(run_interval / (60 * 1000)) + " minutes")
        self.ct = ioloop.PeriodicCallback(JBoxAPI.do_housekeeping, run_interval, self.ioloop)
        self.sigct = ioloop.PeriodicCallback(JBoxAPI.do_signals, 1000, self.ioloop)

    def run(self):
        APIContainer.refresh_container_list()
        JBoxAPI.log_debug("Setting up signal handlers")
        signal.signal(signal.SIGINT, JBoxAPI.signal_handler)
        signal.signal(signal.SIGTERM, JBoxAPI.signal_handler)

        JBoxAPI.log_debug("Starting ioloops")
        self.ct.start()
        self.sigct.start()
        self.ioloop.start()
        JBoxAPI.log_info("Stopped.")

    @staticmethod
    def do_housekeeping():
        is_leader = is_cluster_leader()
        terminating = not is_leader and JBoxAsyncJob.sync_is_terminating()
        if not terminating:
            APIContainer.maintain()
            JBoxAsyncJob.async_plugin_maintenance(is_leader)

    @staticmethod
    def signal_handler(signum, frame):
        JBoxAPI.shutdown = True
        JBoxAPI.log_info("Received signal %r", signum)

    @staticmethod
    def do_signals():
        if JBoxAPI.shutdown:
            JBoxAPI.log_info("Shutting down...")
            ioloop.IOLoop.instance().stop()