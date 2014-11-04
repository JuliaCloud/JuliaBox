#! /usr/bin/env python

import time

import docker

from jbox_util import LoggerMixin, read_config, CloudHelper
from jbox_container import JBoxContainer
from vol import VolMgr


class JBoxContainerBackup(LoggerMixin):
    def __init__(self):
        dckr = docker.Client()
        cfg = read_config()
        cloud_cfg = cfg['cloud_host']

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
                              zone=cloud_cfg['zone'],
                              install_id=cloud_cfg['install_id'])
        VolMgr.configure(dckr, cfg)
        JBoxContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'], cfg['cpu_limit'], cfg['numlocalmax'])

        # backup user files every 1 hour
        # check: configured expiry time must be at least twice greater than this
        self.run_interval = int(cfg['delete_stopped_timeout']) / 2
        if self.run_interval < 3 * 60:
            self.run_interval = 3 * 60

        self.delete_stopped_timeout = int(cfg['delete_stopped_timeout'])
        self.log_info("Backup interval: " + str(self.run_interval / 60) + " minutes")
        self.log_info("Stopped containers would be deleted after " + str(self.delete_stopped_timeout / 60) + " minutes")

    def run(self):
        while True:
            JBoxContainer.backup_and_cleanup(self.delete_stopped_timeout)
            time.sleep(self.run_interval)

if __name__ == "__main__":
    JBoxContainerBackup().run()
