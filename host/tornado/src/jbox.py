#! /usr/bin/env python

import random
import string

import tornado.ioloop
import tornado.web
import tornado.auth
import docker

from jbox_util import read_config, CloudHelper, LoggerMixin
from db import JBoxDB, JBoxUserV2, JBoxInvite, JBoxAccountingV2
from vol import VolMgr
from jbox_container import JBoxContainer
from handlers import JBoxHandler, AdminHandler, MainHandler, AuthHandler, PingHandler, CorsHandler


class JBox(LoggerMixin):
    cfg = None

    def __init__(self):
        cfg = JBox.cfg = read_config()
        dckr = docker.Client()
        cloud_cfg = cfg['cloud_host']

        JBoxHandler.configure(cfg)

        JBoxDB.configure(cfg)
        if 'jbox_users_v2' in cloud_cfg:
            JBoxUserV2.NAME = cloud_cfg['jbox_users_v2']
        if 'jbox_invites' in cloud_cfg:
            JBoxInvite.NAME = cloud_cfg['jbox_invites']
        if 'jbox_accounting_v2' in cloud_cfg:
            JBoxAccountingV2.NAME = cloud_cfg['jbox_accounting_v2']

        CloudHelper.configure(has_s3=cloud_cfg['s3'],
                              has_dynamodb=cloud_cfg['dynamodb'],
                              has_cloudwatch=cloud_cfg['cloudwatch'],
                              has_autoscale=cloud_cfg['autoscale'],
                              has_route53=cloud_cfg['route53'],
                              has_ebs=cloud_cfg['ebs'],
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
            CloudHelper.deregister_instance_dns()
        except:
            CloudHelper.log_info("No prior dns registration found for the instance")
        CloudHelper.register_instance_dns()
        JBoxContainer.publish_container_stats()
        self.ct.start()
        self.ioloop.start()

    @staticmethod
    def do_housekeeping():
        server_delete_timeout = JBox.cfg['expire']
        JBoxContainer.maintain(max_timeout=server_delete_timeout, inactive_timeout=JBox.cfg['inactivity_timeout'],
                               protected_names=JBox.cfg['protected_docknames'])
        if JBox.cfg['cloud_host']['scale_down'] and (JBoxContainer.num_active() == 0) and \
                (JBoxContainer.num_stopped() == 0) and CloudHelper.should_terminate():
            JBox.log_info("terminating to scale down")
            try:
                CloudHelper.deregister_instance_dns()
            except:
                CloudHelper.log_error("Error deregistering instance dns")
            CloudHelper.terminate_instance()


if __name__ == "__main__":
    JBox().run()
