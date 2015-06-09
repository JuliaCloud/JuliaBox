#! /usr/bin/env python

import os
import sys
import shutil

import docker

from db import JBoxDynConfig
from jbox_util import read_config, LoggerMixin
from juliabox import db
from juliabox.cloud.aws import CloudHost
from vol import VolMgr, JBoxVol

if __name__ == "__main__":
    dckr = docker.Client()
    cfg = read_config()
    cloud_cfg = cfg['cloud_host']

    LoggerMixin.setup_logger(level=cfg['root_log_level'])
    LoggerMixin.DEFAULT_LEVEL = cfg['jbox_log_level']

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
    ts = JBoxVol._get_user_home_timestamp()
    VolMgr.log_debug("user_home_timestamp: %s", ts.strftime("%Y%m%d_%H%M"))

    img_dir, img_file = os.path.split(JBoxVol.USER_HOME_IMG)
    new_img_file_name = 'user_home_' + ts.strftime("%Y%m%d_%H%M") + '.tar.gz'
    new_img_file = os.path.join(img_dir, new_img_file_name)
    shutil.copyfile(JBoxVol.USER_HOME_IMG, new_img_file)

    VolMgr.log_debug("new image file is at : %s", new_img_file)

    bucket = 'juliabox-user-home-templates'

    VolMgr.log_debug("pushing new image file to s3 at: %s", bucket)
    CloudHost.push_file_to_s3(bucket, new_img_file)

    # JuliaBoxTest JuliaBox
    clusters = sys.argv[1] if (len(sys.argv) > 1) else ['JuliaBoxTest']

    for cluster in clusters:
        VolMgr.log_debug("setting image for cluster: %s", cluster)
        JBoxDynConfig.set_user_home_image(cluster, bucket, new_img_file_name)
