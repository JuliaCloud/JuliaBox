#! /usr/bin/env python

import random
import string

import tornado.ioloop
import tornado.web
import tornado.auth
import docker
from cloud.aws import CloudHost

import db
from db import JBoxDynConfig, JBoxUserV2, is_cluster_leader
from jbox_util import read_config, LoggerMixin
from vol import VolMgr
from jbox_container import JBoxContainer
from handlers import JBoxHandler, AdminHandler, MainHandler, AuthHandler, PingHandler, CorsHandler


class JBox(LoggerMixin):
    cfg = None

    def __init__(self):
        dckr = docker.Client()
        cfg = JBox.cfg = read_config()
        cloud_cfg = cfg['cloud_host']

        LoggerMixin.setup_logger(level=cfg['root_log_level'])
        LoggerMixin.DEFAULT_LEVEL = cfg['jbox_log_level']

        JBoxHandler.configure(cfg)
        db.configure_db(cfg)

        CloudHost.configure(has_s3=cloud_cfg['s3'],
                            has_dynamodb=cloud_cfg['dynamodb'],
                            has_cloudwatch=cloud_cfg['cloudwatch'],
                            has_autoscale=cloud_cfg['autoscale'],
                            has_route53=cloud_cfg['route53'],
                            has_ebs=cloud_cfg['ebs'],
                            has_ses=cloud_cfg['ses'],
                            scale_up_at_load=cloud_cfg['scale_up_at_load'],
                            scale_up_policy=cloud_cfg['scale_up_policy'],
                            autoscale_group=cloud_cfg['autoscale_group'],
                            route53_domain=cloud_cfg['route53_domain'],
                            region=cloud_cfg['region'],
                            install_id=cloud_cfg['install_id'])

        VolMgr.configure(dckr, cfg)
        JBoxContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'], cfg['cpu_limit'],
                                cfg['numlocalmax'], cfg['async_job_port'])

        self.application = tornado.web.Application([
            (r"/", MainHandler),
            (r"/hostlaunchipnb/", AuthHandler),
            (r"/hostadmin/", AdminHandler),
            (r"/ping/", PingHandler),
            (r"/cors/", CorsHandler)
        ])
        cookie_secret = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
        self.application.settings["cookie_secret"] = cookie_secret
        self.application.settings["google_oauth"] = cfg["google_oauth"]
        self.application.listen(cfg["port"])

        self.ioloop = tornado.ioloop.IOLoop.instance()

        # run container maintainence every 5 minutes
        run_interval = 5 * 60 * 1000
        self.log_info("Container maintenance every " + str(run_interval / (60 * 1000)) + " minutes")
        self.ct = tornado.ioloop.PeriodicCallback(JBox.do_housekeeping, run_interval, self.ioloop)

    def run(self):
        try:
            CloudHost.deregister_instance_dns()
        except:
            CloudHost.log_info("No prior dns registration found for the instance")
        CloudHost.register_instance_dns()
        JBoxContainer.publish_container_stats()
        JBox.do_update_user_home_image()
        JBoxContainer.async_refresh_disks()
        self.ct.start()
        self.ioloop.start()

    @staticmethod
    def do_update_user_home_image():
        if VolMgr.has_update_for_user_home_image():
            if not VolMgr.update_user_home_image(fetch=False):
                JBoxContainer.async_update_user_home_image()

    @staticmethod
    def do_housekeeping():
        JBox.do_update_user_home_image()

        server_delete_timeout = JBox.cfg['expire']
        JBoxContainer.maintain(max_timeout=server_delete_timeout, inactive_timeout=JBox.cfg['inactivity_timeout'],
                               protected_names=JBox.cfg['protected_docknames'])
        if JBox.cfg['cloud_host']['scale_down'] and (JBoxContainer.num_active() == 0) and \
                (JBoxContainer.num_stopped() == 0) and CloudHost.should_terminate():
            JBox.log_info("terminating to scale down")
            try:
                CloudHost.deregister_instance_dns()
            except:
                CloudHost.log_error("Error deregistering instance dns")
            CloudHost.terminate_instance()
        elif is_cluster_leader():
            CloudHost.log_error("I am the cluster leader")
            max_rate = JBoxDynConfig.get_registration_hourly_rate(CloudHost.INSTALL_ID)
            rate = JBoxUserV2.count_created(1)
            reg_allowed = JBoxDynConfig.get_allow_registration(CloudHost.INSTALL_ID)
            CloudHost.log_debug("registration allowed: %r, rate: %d, max allowed: %d", reg_allowed, rate, max_rate)

            if (reg_allowed and (rate > max_rate*1.1)) or ((not reg_allowed) and (rate < max_rate*0.9)):
                reg_allowed = not reg_allowed
                CloudHost.log_info("Changing registration allowed to %r", reg_allowed)
                JBoxDynConfig.set_allow_registration(CloudHost.INSTALL_ID, reg_allowed)

            if reg_allowed:
                num_pending_activations = JBoxUserV2.count_pending_activations()
                if num_pending_activations > 0:
                    CloudHost.log_info("scheduling activations for %d pending activations", num_pending_activations)
                    JBoxContainer.async_schedule_activations()


if __name__ == "__main__":
    JBox().run()
