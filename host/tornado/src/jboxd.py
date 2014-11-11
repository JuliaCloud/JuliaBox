#! /usr/bin/env python

import threading
import json

import docker
from cloud.aws import CloudHost

from jbox_util import LoggerMixin, read_config, JBoxAsyncJob, retry
from jbox_container import JBoxContainer
from vol import VolMgr


class JBoxd(LoggerMixin):
    ACTIVE = {}
    LOCK = threading.Lock()

    def __init__(self):
        dckr = docker.Client()
        cfg = read_config()
        cloud_cfg = cfg['cloud_host']

        CloudHost.configure(has_s3=cloud_cfg['s3'],
                              has_dynamodb=cloud_cfg['dynamodb'],
                              has_cloudwatch=cloud_cfg['cloudwatch'],
                              has_autoscale=cloud_cfg['autoscale'],
                              has_route53=cloud_cfg['route53'],
                              has_ebs=cloud_cfg['ebs'],
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

    def run(self):
        while True:
            self.log_debug("Backup daemon waiting for commands...")
            cmd, data = self.queue.recv()

            if cmd == JBoxAsyncJob.CMD_BACKUP_CLEANUP:
                args = (data,)
                fn = JBoxd.backup_and_cleanup
            elif cmd == JBoxAsyncJob.CMD_LAUNCH_SESSION:
                args = (data[0], data[1], data[2])
                fn = JBoxd.launch_session
            else:
                self.log_error("Unknown command " + str(cmd))
                continue

            JBoxd.schedule_thread(cmd, fn, args)

if __name__ == "__main__":
    JBoxd().run()
