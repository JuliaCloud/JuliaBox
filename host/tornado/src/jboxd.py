#! /usr/bin/env python

import threading
import json
import time

import docker
from cloud.aws import CloudHost

import db
from db import JBoxUserV2
from jbox_util import LoggerMixin, read_config, JBoxAsyncJob, retry
from jbox_container import JBoxContainer
from vol import VolMgr


class JBoxd(LoggerMixin):
    ACTIVE = {}
    LOCK = threading.Lock()
    MAX_AUTO_ACTIVATIONS_PER_RUN = 10
    MAX_ACTIVATIONS_PER_SEC = 10
    ACTIVATION_SUBJECT = None
    ACTIVATION_BODY = None
    ACTIVATION_SENDER = None

    def __init__(self):
        dckr = docker.Client()
        cfg = read_config()
        cloud_cfg = cfg['cloud_host']
        user_activation_cfg = cfg['user_activation']

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
        JBoxContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'], cfg['cpu_limit'],
                                cfg['numlocalmax'], cfg['async_job_port'], async_mode=JBoxAsyncJob.MODE_SUB)
        self.log_debug("Backup daemon listening on port: " + str(cfg['async_job_port']))
        self.queue = JBoxContainer.ASYNC_JOB

        JBoxd.MAX_ACTIVATIONS_PER_SEC = user_activation_cfg['max_activations_per_sec']
        JBoxd.MAX_AUTO_ACTIVATIONS_PER_RUN = user_activation_cfg['max_activations_per_run']
        JBoxd.ACTIVATION_SUBJECT = user_activation_cfg['mail_subject']
        JBoxd.ACTIVATION_BODY = user_activation_cfg['mail_body']
        JBoxd.ACTIVATION_SENDER = user_activation_cfg['sender']

    @staticmethod
    def is_duplicate(sign):
        return sign in JBoxd.ACTIVE

    @staticmethod
    def schedule_thread(cmd, target, args):
        sign = json.dumps({'cmd': cmd, 'args': args})
        JBoxd.log_debug("received command " + sign)

        JBoxd.LOCK.acquire()
        if JBoxd.is_duplicate(sign):
            JBoxd.log_debug("already processing command " + sign)
            JBoxd.LOCK.release()
            return

        t = threading.Thread(target=target, args=args, name=sign)
        JBoxd.ACTIVE[sign] = t
        JBoxd.LOCK.release()
        JBoxd.log_debug("scheduled " + sign)
        t.start()

    @staticmethod
    def finish_thread():
        JBoxd.LOCK.acquire()
        sign = threading.current_thread().name
        del JBoxd.ACTIVE[sign]
        JBoxd.LOCK.release()
        JBoxd.log_debug("finished " + sign)

    @staticmethod
    def backup_and_cleanup(dockid):
        try:
            cont = JBoxContainer(dockid)
            cont.stop()
            cont.delete(backup=True)
        finally:
            JBoxd.finish_thread()

    @staticmethod
    def _is_scheduled(cmd, args):
        sign = json.dumps({'cmd': cmd, 'args': args})
        JBoxd.LOCK.acquire()
        ret = JBoxd.is_duplicate(sign)
        JBoxd.LOCK.release()
        return ret

    @staticmethod
    @retry(15, 0.5, backoff=1.5)
    def _wait_for_session_backup(sessname):
        cont = JBoxContainer.get_by_name(sessname)
        if (cont is not None) and JBoxd._is_scheduled(JBoxAsyncJob.CMD_BACKUP_CLEANUP, (cont.dockid,)):
            return False
        return True

    @staticmethod
    def launch_session(name, email, reuse=True):
        try:
            JBoxd._wait_for_session_backup(name)
            VolMgr.refresh_disk_use_status()
            JBoxContainer.launch_by_name(name, email, reuse=reuse)
        finally:
            JBoxd.finish_thread()

    @staticmethod
    def auto_activate():
        try:
            num_mails_24h, rate = CloudHost.get_email_rates()
            rate_per_second = min(JBoxd.MAX_ACTIVATIONS_PER_SEC, rate)
            num_mails = min(JBoxd.MAX_AUTO_ACTIVATIONS_PER_RUN, num_mails_24h)

            JBoxd.log_info("Will activate max %d users at %d per second. AWS limits: %d mails at %d per second",
                           num_mails, rate_per_second,
                           num_mails_24h, rate)
            user_ids = JBoxUserV2.get_pending_activations(num_mails)
            JBoxd.log_info("Got %d user_ids to be activated", len(user_ids))

            for user_id in user_ids:
                JBoxd.log_info("Activating %s", user_id)

                # send email by SES
                CloudHost.send_email(user_id, JBoxd.ACTIVATION_SENDER, JBoxd.ACTIVATION_SUBJECT, JBoxd.ACTIVATION_BODY)

                # set user as activated
                user = JBoxUserV2(user_id)
                user.set_activation_state(JBoxUserV2.ACTIVATION_CODE_AUTO, JBoxUserV2.ACTIVATION_GRANTED)
                user.save()

                rate_per_second -= 1
                if rate_per_second <= 0:
                    time.sleep(1)
                    rate_per_second = min(JBoxd.MAX_ACTIVATIONS_PER_SEC, rate)
        finally:
            JBoxd.finish_thread()

    @staticmethod
    def update_user_home_image():
        try:
            VolMgr.update_user_home_image(fetch=True)
        finally:
            JBoxd.finish_thread()

    def run(self):
        while True:
            self.log_debug("JBox daemon waiting for commands...")
            cmd, data = self.queue.recv()

            if cmd == JBoxAsyncJob.CMD_BACKUP_CLEANUP:
                args = (data,)
                fn = JBoxd.backup_and_cleanup
            elif cmd == JBoxAsyncJob.CMD_LAUNCH_SESSION:
                args = (data[0], data[1], data[2])
                fn = JBoxd.launch_session
            elif cmd == JBoxAsyncJob.CMD_AUTO_ACTIVATE:
                args = ()
                fn = JBoxd.auto_activate
            elif cmd == JBoxAsyncJob.CMD_UPDATE_USER_HOME_IMAGE:
                args = ()
                fn = JBoxd.update_user_home_image
            else:
                self.log_error("Unknown command " + str(cmd))
                continue

            JBoxd.schedule_thread(cmd, fn, args)

if __name__ == "__main__":
    JBoxd().run()
