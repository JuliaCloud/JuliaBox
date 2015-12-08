import socket
import signal
import datetime
import os

import tornado.ioloop
import tornado.web
import tornado.auth
from tornado.httpclient import AsyncHTTPClient

from cloud import Compute, JBPluginCloud
import db
from db import JBoxDynConfig, JBoxUserV2, is_cluster_leader, JBPluginDB
from jbox_tasks import JBoxAsyncJob
from jbox_util import LoggerMixin, JBoxCfg
from jbox_tasks import JBPluginTask
from vol import VolMgr, JBoxVol
from juliabox.interactive import SessContainer
from handlers import AdminHandler, MainHandler, PingHandler, CorsHandler
from handlers import JBPluginHandler, JBPluginUI


class JBox(LoggerMixin):
    shutdown = False

    def __init__(self):
        LoggerMixin.configure()
        db.configure()
        Compute.configure()
        SessContainer.configure()
        VolMgr.configure()

        JBoxAsyncJob.configure()
        JBoxAsyncJob.init(JBoxAsyncJob.MODE_PUB)

        self.application = tornado.web.Application(handlers=[
            (r"/", MainHandler),
            (r"/jboxadmin/", AdminHandler),
            (r"/jboxping/", PingHandler),
            (r"/jboxcors/", CorsHandler)
        ])
        JBPluginHandler.add_plugin_handlers(self.application)
        JBPluginUI.create_include_files()

        # cookie_secret = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
        # use sesskey as cookie secret to be able to span multiple tornado servers
        self.application.settings["cookie_secret"] = JBoxCfg.get('sesskey')
        self.application.settings["plugin_features"] = JBox.get_pluggedin_features()
        self.application.listen(JBoxCfg.get('interactive.manager_port'), address=socket.gethostname())
        self.application.listen(JBoxCfg.get('interactive.manager_port'), address='localhost')

        self.ioloop = tornado.ioloop.IOLoop.instance()

        # run container maintainence every 5 minutes
        run_interval = 5 * 60 * 1000
        self.log_info("Container maintenance every " + str(run_interval / (60 * 1000)) + " minutes")
        self.ct = tornado.ioloop.PeriodicCallback(JBox.do_housekeeping, run_interval, self.ioloop)
        self.sigct = tornado.ioloop.PeriodicCallback(JBox.do_signals, 1000, self.ioloop)

        # or configure cacerts
        AsyncHTTPClient.configure(None, defaults=dict(validate_cert=None))

    @staticmethod
    def get_pluggedin_features():
        feature_providers = dict()
        for pluginclass in [JBPluginTask, JBPluginDB, JBPluginHandler, JBPluginUI,
                            JBoxVol, JBPluginCloud]:
            for plugin in pluginclass.plugins:
                for feature in plugin.provides:
                    if feature in feature_providers:
                        feature_providers[feature].append(plugin.__name__)
                    else:
                        feature_providers[feature] = [plugin.__name__]
        return feature_providers

    def run(self):
        JBox.do_update_user_home_image()
        JBoxAsyncJob.async_refresh_disks()

        JBox.log_debug("Setting up signal handlers")
        signal.signal(signal.SIGINT, JBox.signal_handler)
        signal.signal(signal.SIGTERM, JBox.signal_handler)

        JBox.log_debug("Starting ioloops")
        self.ct.start()
        self.sigct.start()
        self.ioloop.start()
        JBox.log_info("Stopped.")

    @staticmethod
    def do_update_user_home_image():
        if VolMgr.has_update_for_user_home_image():
            if not VolMgr.update_user_home_image(fetch=False):
                JBoxAsyncJob.async_update_user_home_image()

    @staticmethod
    def monitor_registrations():
        max_rate = JBoxDynConfig.get_registration_hourly_rate(Compute.get_install_id())
        rate = JBoxUserV2.count_created(1)
        reg_allowed = JBoxDynConfig.get_allow_registration(Compute.get_install_id())
        JBox.log_debug("registration allowed: %r, rate: %d, max allowed: %d", reg_allowed, rate, max_rate)

        if (reg_allowed and (rate > max_rate*1.1)) or ((not reg_allowed) and (rate < max_rate*0.9)):
            reg_allowed = not reg_allowed
            JBox.log_warn("Changing registration allowed to %r", reg_allowed)
            JBoxDynConfig.set_allow_registration(Compute.get_install_id(), reg_allowed)

        if reg_allowed:
            num_pending_activations = JBoxUserV2.count_pending_activations()
            if num_pending_activations > 0:
                JBox.log_info("scheduling activations for %d pending activations", num_pending_activations)
                JBoxAsyncJob.async_schedule_activations()

    @staticmethod
    def update_juliabox_status():
        instances = Compute.get_all_instances()

        in_error = 0
        HTML = "<html><body><center><pre>\nJuliaBox is Up.\n\nLast updated: " + datetime.datetime.now().isoformat() + " UTC\n\nLoads: "

        for inst in instances:
            try:
                status = JBoxAsyncJob.sync_api_status(inst)['data']
                HTML += (str(status['load']) + '% ')
            except:
                in_error += 1
                pass

        HTML += ("\n\nErrors: " + str(in_error) + "\n\nAWS Status: <a href='http://status.aws.amazon.com/'>status.aws.amazon.com</a></pre></center></body></html>")

        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_BUCKETSTORE)
        bkt = JBoxCfg.get("cloud_host.status_bucket")
        if plugin is not None and bkt is not None:
            try:
                f = open("/tmp/index.html", "w")
                f.write(HTML)
                f.close()
                plugin.push(bkt, "/tmp/index.html")
            finally:
                os.remove("/tmp/index.html")
        else:
            JBox.log_debug("Status: %s", HTML)

        return None

    @staticmethod
    def do_housekeeping():
        terminating = False
        server_delete_timeout = JBoxCfg.get('interactive.expire')
        inactive_timeout = JBoxCfg.get('interactive.inactivity_timeout')
        SessContainer.maintain(max_timeout=server_delete_timeout, inactive_timeout=inactive_timeout)
        is_leader = is_cluster_leader()

        if is_leader:
            terminating = False
        else:
            try:
                terminating = JBoxAsyncJob.sync_is_terminating()
                if terminating['code'] == 0:
                    terminating = terminating['data']
                else:
                    JBox.log_error("Error checking if instance is terminating. Assuming False.")
                    terminating = False
            except:
                JBox.log_error("Exception checking if instance is terminating. Assuming False.")
                terminating = False

        if is_leader:
            JBox.log_info("I am the cluster leader")
            JBox.update_juliabox_status()
            JBox.monitor_registrations()
            if not JBoxDynConfig.is_stat_collected_within(Compute.get_install_id(), 1):
                JBoxAsyncJob.async_collect_stats()

        if terminating:
            JBox.log_warn("terminating to scale down")
        else:
            JBox.do_update_user_home_image()
            JBoxAsyncJob.async_plugin_maintenance(is_leader)

    @staticmethod
    def signal_handler(signum, frame):
        JBox.shutdown = True
        JBox.log_info("Received signal %r", signum)

    @staticmethod
    def do_signals():
        if JBox.shutdown:
            JBox.log_info("Shutting down...")
            tornado.ioloop.IOLoop.instance().stop()