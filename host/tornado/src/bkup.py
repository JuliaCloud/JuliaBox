#! /usr/bin/env python

import os
import time

import docker

from jbox_util import LoggerMixin, read_config, make_sure_path_exists, CloudHelper
from jbox_container import JBoxContainer


class JBoxContainerBackup(LoggerMixin):
    def __init__(self):
        dckr = docker.Client()
        cfg = read_config()

        backup_location = os.path.expanduser(cfg['backup_location'])
        user_home_img = os.path.expanduser(cfg['user_home_image'])
        mnt_location = os.path.expanduser(cfg['mnt_location'])
        cloud_cfg = cfg['cloud_host']
        backup_bucket = cloud_cfg['backup_bucket']
        make_sure_path_exists(backup_location)

        CloudHelper.configure(has_s3=cloud_cfg['s3'],
                              has_dynamodb=cloud_cfg['dynamodb'],
                              has_cloudwatch=cloud_cfg['cloudwatch'],
                              has_autoscale=cloud_cfg['autoscale'],
                              has_route53=cloud_cfg['route53'],
                              scale_up_at_load=cloud_cfg['scale_up_at_load'],
                              scale_up_policy=cloud_cfg['scale_up_policy'],
                              autoscale_group=cloud_cfg['autoscale_group'],
                              route53_domain=cloud_cfg['route53_domain'],
                              region=cloud_cfg['region'],
                              install_id=cloud_cfg['install_id'])
        JBoxContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'], cfg['cpu_limit'], cfg['disk_limit'],
                                [os.path.join(mnt_location, '${DISK_ID}')], mnt_location, backup_location,
                                user_home_img, cfg['numlocalmax'], cfg["numdisksmax"], backup_bucket=backup_bucket)

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
