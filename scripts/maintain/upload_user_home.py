#! /usr/bin/env python

import os
import sys
import shutil
from os.path import expanduser

import docker

from juliabox.db import JBoxDynConfig
from juliabox import db
from juliabox.jbox_util import JBoxCfg, LoggerMixin
from juliabox.jbox_container import JBoxContainer
from juliabox.cloud.aws import CloudHost
from juliabox.vol import VolMgr, JBoxVol


def copy_for_upload(tstamp):
    img_dir, img_file = os.path.split(JBoxVol.USER_HOME_IMG)
    new_img_file_name = 'user_home_' + tstamp + '.tar.gz'
    new_img_file = os.path.join(img_dir, new_img_file_name)
    shutil.copyfile(JBoxVol.USER_HOME_IMG, new_img_file)

    new_pkg_file_name = 'julia_packages_' + tstamp + '.tar.gz'
    new_pkg_file = os.path.join(img_dir, new_pkg_file_name)
    shutil.copyfile(JBoxVol.PKG_IMG, new_pkg_file)

    VolMgr.log_debug("new image files : %s, %s", new_img_file, new_pkg_file)
    return new_img_file, new_pkg_file


def copy_for_boot():
    for f in (JBoxVol.USER_HOME_IMG, JBoxVol.PKG_IMG):
        dname, fname = os.path.split(f)
        copyname = expanduser(os.path.join("~", fname))
        shutil.copyfile(f, copyname)


if __name__ == "__main__":
    conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../engine/conf'))
    conf_file = os.path.join(conf_dir, 'tornado.conf')
    user_conf_file = os.path.join(conf_dir, 'jbox.user')

    JBoxCfg.read(conf_file, user_conf_file)
    JBoxCfg.dckr = docker.Client()

    LoggerMixin.configure()
    db.configure()
    CloudHost.configure()
    JBoxContainer.configure()
    VolMgr.configure()

    ts = JBoxVol._get_user_home_timestamp()
    tsstr = ts.strftime("%Y%m%d_%H%M")
    VolMgr.log_debug("user_home_timestamp: %s", tsstr)

    imgf, pkgf = copy_for_upload(tsstr)
    copy_for_boot()

    bucket = 'juliabox-user-home-templates'

    VolMgr.log_debug("pushing new image files to s3 at: %s", bucket)
    CloudHost.push_file_to_s3(bucket, imgf)
    CloudHost.push_file_to_s3(bucket, pkgf)

    # JuliaBoxTest JuliaBox
    clusters = sys.argv[1] if (len(sys.argv) > 1) else ['JuliaBoxTest']

    for cluster in clusters:
        VolMgr.log_debug("setting image for cluster: %s", cluster)
        JBoxDynConfig.set_user_home_image(cluster, bucket, pkgf, imgf)
