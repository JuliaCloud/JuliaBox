#! /usr/bin/env python

import docker, os
from jbox_util import read_config, make_sure_path_exists
from jbox_container import JBoxContainer

if __name__ == "__main__":
    dckr = docker.Client()
    cfg = read_config()
    backup_location = os.path.expanduser(cfg['backup_location'])
    backup_bucket = cfg['backup_bucket']
    make_sure_path_exists(backup_location)
    JBoxContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'], cfg['cpu_limit'], [os.path.join(backup_location, '${CNAME}')], backup_location, backup_bucket=backup_bucket)
    
    JBoxContainer.backup_all()

