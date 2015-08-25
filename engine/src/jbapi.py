#! /usr/bin/env python

import docker
import os
from zmq.eventloop import ioloop

from juliabox.srvr_jbapi import JBoxAPI
from juliabox.jbox_util import JBoxCfg

if __name__ == "__main__":
    ioloop.install()

    conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../conf'))
    conf_file = os.path.join(conf_dir, 'tornado.conf')
    user_conf_file = os.path.join(conf_dir, 'jbox.user')

    JBoxCfg.read(conf_file, user_conf_file)
    JBoxCfg.dckr = docker.Client()

    JBoxAPI().run()
