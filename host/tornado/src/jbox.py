#! /usr/bin/env python

from jbox_util import log_info, esc_sessname, read_config, make_sure_path_exists, unquote, CloudHelper
from db.user_v2 import JBoxUserV2
from db.invites import JBoxInvite
from db.accounting_v2 import JBoxAccountingV2
from jbox_container import JBoxContainer
from jbox_crypto import signstr

import tornado.ioloop, tornado.web, tornado.auth
import base64, json, os.path, random, string
import docker

import datetime, traceback, isodate, pytz, httplib2
from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI
from oauth2client.client import OAuth2Credentials, _extract_id_token

from handlers.admin import AdminHandler
from handlers.main import MainHandler
from handlers.auth import AuthHandler
from handlers.ping import PingHandler

def do_housekeeping():
    server_delete_timeout = cfg['expire'];
    JBoxContainer.maintain(max_timeout=server_delete_timeout, inactive_timeout=cfg['inactivity_timeout'], protected_names=cfg['protected_docknames'])
    if cfg['scale_down'] and (JBoxContainer.num_active() == 0) and (JBoxContainer.num_stopped() == 0) and CloudHelper.should_terminate():
        log_info("terminating to scale down")
        #do_backups()
        CloudHelper.terminate_instance()
    

if __name__ == "__main__":
    dckr = docker.Client()
    cfg = read_config()
    
    cloud_cfg = cfg['cloud_host']
    CloudHelper.configure(has_s3=cloud_cfg['s3'], has_dynamodb=cloud_cfg['dynamodb'], has_cloudwatch=cloud_cfg['cloudwatch'], region=cloud_cfg['region'], install_id=cloud_cfg['install_id'])
    
    backup_location = os.path.expanduser(cfg['backup_location'])
    user_home_img = os.path.expanduser(cfg['user_home_image'])
    mnt_location = os.path.expanduser(cfg['mnt_location'])
    backup_bucket = cloud_cfg['backup_bucket']
    make_sure_path_exists(backup_location)
    JBoxContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'], cfg['cpu_limit'], cfg['disk_limit'], 
                            [os.path.join(mnt_location, '${DISK_ID}')], mnt_location, backup_location, user_home_img, 
                            cfg['numlocalmax'], cfg["numdisksmax"], backup_bucket=backup_bucket)
    JBoxContainer.publish_container_stats()
    
    JBoxUserV2._init(table_name=cloud_cfg.get('jbox_users_v2', 'jbox_users_v2'), enckey=cfg['sesskey'])
    #JBoxInvite._create_table()
    JBoxInvite._init(table_name=cloud_cfg.get('jbox_invites', 'jbox_invites'), enckey=cfg['sesskey'])
    JBoxAccountingV2._init(table_name=cloud_cfg.get('jbox_accounting_v2', 'jbox_accounting_v2'))
    
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/hostlaunchipnb/", AuthHandler),
        (r"/hostadmin/", AdminHandler),
        (r"/ping/", PingHandler)
    ])
    application.settings["cookie_secret"] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    application.settings["google_oauth"] = cfg["google_oauth"]
    application.listen(cfg["port"])
    
    ioloop = tornado.ioloop.IOLoop.instance()

    # run container maintainence every 5 minutes
    run_interval = 5*60*1000
    log_info("Container maintenance every " + str(run_interval/(60*1000)) + " minutes")
    ct = tornado.ioloop.PeriodicCallback(do_housekeeping, run_interval, ioloop)
    ct.start()
    
    ioloop.start()


