#! /usr/bin/env python

import docker
import os
from juliabox.srvr_jboxd import JBoxd
from juliabox.jbox_util import JBoxCfg


if __name__ == "__main__":
    conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../conf'))
    conf_file = os.path.join(conf_dir, 'tornado.conf')
    user_conf_file = os.path.join(conf_dir, 'jbox.user')

    JBoxCfg.read(conf_file, user_conf_file)
    JBoxCfg.dckr = docker.Client()

    JBoxd().run()
