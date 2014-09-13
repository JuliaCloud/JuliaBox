#! /usr/bin/env python

import docker, os, time
from jbox_util import read_config, make_sure_path_exists, log_info, CloudHelper
from jbox_container import JBoxContainer

if __name__ == "__main__":
    dckr = docker.Client()
    cfg = read_config()
    backup_location = os.path.expanduser(cfg['backup_location'])
    user_home_img = os.path.expanduser(cfg['user_home_image'])
    mnt_location = os.path.expanduser(cfg['mnt_location'])
    cloud_cfg = cfg['cloud_host']
    backup_bucket = cloud_cfg['backup_bucket']
    make_sure_path_exists(backup_location)
    
    CloudHelper.configure(has_s3=cloud_cfg['s3'], has_dynamodb=cloud_cfg['dynamodb'], has_cloudwatch=cloud_cfg['cloudwatch'], region=cloud_cfg['region'], install_id=cloud_cfg['install_id'])    
    JBoxContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'], cfg['cpu_limit'], cfg['disk_limit'], 
                            [os.path.join(mnt_location, '${DISK_ID}')], mnt_location, backup_location, user_home_img, 
                            cfg['numlocalmax'], cfg["numdisksmax"], backup_bucket=backup_bucket)

    # backup user files every 1 hour
    # check: configured expiry time must be at least twice greater than this
    run_interval = int(cfg['delete_stopped_timeout'])/2
    if run_interval < 3*60:
        run_interval = 3*60
        
    log_info("Backup interval: " + str(run_interval/60) + " minutes")
    log_info("Stopped containers would be deleted after " + str(int(cfg['delete_stopped_timeout'])/60) + " minutes")
    
    while(True):
        JBoxContainer.backup_and_cleanup(int(cfg['delete_stopped_timeout']))
        time.sleep(run_interval)
