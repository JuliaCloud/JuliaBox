#! /usr/bin/env python

import os
import sys
import shutil

import docker

from juliabox.db import JBoxDynConfig
from juliabox import db
from juliabox.jbox_util import JBoxCfg, LoggerMixin
from juliabox.cloud.aws import CloudHost
from juliabox.vol import VolMgr, JBoxVol

if __name__ == "__main__":
    conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../host/tornado/conf'))
    conf_file = os.path.join(conf_dir, 'tornado.conf')
    user_conf_file = os.path.join(conf_dir, 'jbox.user')

    JBoxCfg.read(conf_file, user_conf_file)
    JBoxCfg.dckr = docker.Client()

    LoggerMixin.configure()
    db.configure()
    CloudHost.configure()
    VolMgr.configure()

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
