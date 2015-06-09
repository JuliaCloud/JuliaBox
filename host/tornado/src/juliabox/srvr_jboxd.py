import threading
import json
import time
import datetime
import pytz

import docker

from cloud.aws import CloudHost
import db
from db import JBoxUserV2, JBoxDynConfig, JBoxDiskState, JBoxSessionProps
from jbox_tasks import JBoxAsyncJob
from jbox_util import LoggerMixin, read_config, retry, unique_sessname
from jbox_container import JBoxContainer
from vol import VolMgr, JBoxLoopbackVol
from parallel import UserCluster


def jboxd_method(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except:
            JBoxd.log_exception("Exception in jboxd_method %s", f.func_name)
            time.sleep(2)
        finally:
            JBoxd.finish_thread()

    wrapper.__name__ = 'jboxd_method_' + f.func_name
    return wrapper


class JBoxd(LoggerMixin):
    ACTIVE = {}
    LOCK = threading.Lock()
    MAX_AUTO_ACTIVATIONS_PER_RUN = 10
    MAX_ACTIVATIONS_PER_SEC = 10
    ACTIVATION_SUBJECT = None
    ACTIVATION_BODY = None
    ACTIVATION_SENDER = None
    QUEUE = None

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
        JBoxAsyncJob.configure(cfg, JBoxAsyncJob.MODE_SUB)
        JBoxContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'], cfg['cpu_limit'], cfg['numlocalmax'])
        self.log_debug("Backup daemon listening on ports: %s", repr(cfg['async_job_ports']))
        JBoxd.QUEUE = JBoxAsyncJob.get()

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
    @jboxd_method
    def backup_and_cleanup(dockid):
        cont = JBoxContainer(dockid)
        cont.stop()
        cont.delete(backup=True)

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
            JBoxd.log_debug("Waiting for backup of session %s", sessname)
            return False
        return True

    @staticmethod
    @jboxd_method
    def launch_session(name, email, reuse=True):
        JBoxd._wait_for_session_backup(name)
        VolMgr.refresh_disk_use_status()
        JBoxContainer.launch_by_name(name, email, reuse=reuse)

    @staticmethod
    @jboxd_method
    def auto_activate():
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

    @staticmethod
    @jboxd_method
    def update_user_home_image():
        VolMgr.update_user_home_image(fetch=True)
        JBoxLoopbackVol.refresh_all_disks()

    @staticmethod
    @jboxd_method
    def update_disk_states():
        detached_disks = JBoxDiskState.get_detached_disks()
        time_now = datetime.datetime.now(pytz.utc)
        for disk_key in detached_disks:
            disk_info = JBoxDiskState(disk_key=disk_key)
            user_id = disk_info.get_user_id()
            sess_props = JBoxSessionProps(unique_sessname(user_id))
            incomplete_snapshots = []
            modified = False
            for snap_id in disk_info.get_snapshot_ids():
                if not CloudHost.is_snapshot_complete(snap_id):
                    incomplete_snapshots.append(snap_id)
                    continue
                JBoxd.log_debug("updating latest snapshot of user %s to %s", user_id, snap_id)
                old_snap_id = sess_props.get_snapshot_id()
                sess_props.set_snapshot_id(snap_id)
                modified = True
                if old_snap_id is not None:
                    CloudHost.delete_snapshot(old_snap_id)
            if modified:
                sess_props.save()
                disk_info.set_snapshot_ids(incomplete_snapshots)
                disk_info.save()
            if len(incomplete_snapshots) == 0:
                if (time_now - disk_info.get_detach_time()).total_seconds() > 24*60*60:
                    vol_id = disk_info.get_volume_id()
                    JBoxd.log_debug("volume %s for user %s unused for too long", vol_id, user_id)
                    disk_info.delete()
                    CloudHost.detach_volume(vol_id, delete=True)
            else:
                JBoxd.log_debug("ongoing snapshots of user %s: %r", user_id, incomplete_snapshots)

    @staticmethod
    @jboxd_method
    def terminate_or_delete_cluster(cluster_id):
        uc = UserCluster(None, gname=cluster_id)
        uc.terminate_or_delete()

    @staticmethod
    @jboxd_method
    def refresh_disks():
        if JBoxd._is_scheduled(JBoxAsyncJob.CMD_UPDATE_USER_HOME_IMAGE, ()):
            return
        JBoxLoopbackVol.refresh_all_disks()

    @staticmethod
    @jboxd_method
    def collect_stats():
        VolMgr.publish_stats()
        db.publish_stats()
        JBoxDynConfig.set_stat_collected_date(CloudHost.INSTALL_ID)

    def process_offline(self):
        self.log_debug("processing offline...")
        cmd, data = JBoxd.QUEUE.recv()
        args = ()

        if cmd == JBoxAsyncJob.CMD_BACKUP_CLEANUP:
            args = (data,)
            fn = JBoxd.backup_and_cleanup
        elif cmd == JBoxAsyncJob.CMD_LAUNCH_SESSION:
            args = (data[0], data[1], data[2])
            fn = JBoxd.launch_session
        elif cmd == JBoxAsyncJob.CMD_AUTO_ACTIVATE:
            fn = JBoxd.auto_activate
        elif cmd == JBoxAsyncJob.CMD_UPDATE_USER_HOME_IMAGE:
            fn = JBoxd.update_user_home_image
        elif cmd == JBoxAsyncJob.CMD_REFRESH_DISKS:
            fn = JBoxd.refresh_disks
        elif cmd == JBoxAsyncJob.CMD_COLLECT_STATS:
            fn = JBoxd.collect_stats
        elif cmd == JBoxAsyncJob.CMD_UPDATE_DISK_STATES:
            fn = JBoxd.update_disk_states
        elif cmd == JBoxAsyncJob.CMD_TERMINATE_OR_DELETE_CLUSTER:
            fn = JBoxd.terminate_or_delete_cluster
            args = (data,)
        else:
            self.log_error("Unknown command " + str(cmd))
            return

        JBoxd.schedule_thread(cmd, fn, args)

    @staticmethod
    def get_session_status():
        ret = {}
        jsonobj = JBoxContainer.DCKR.containers(all=all)
        for c in jsonobj:
            name = c["Names"][0] if (("Names" in c) and (c["Names"] is not None)) else c["Id"][0:12]
            ret[name] = c["Status"]

        return ret

    @staticmethod
    @jboxd_method
    def process_and_respond():
        def _callback(cmd, data):
            try:
                if cmd == JBoxAsyncJob.CMD_SESSION_STATUS:
                    resp = {'code': 0, 'data': JBoxd.get_session_status()}
                else:
                    resp = {'code:': -2, 'data': ('unknown command %s' % (repr(cmd,)))}
            except Exception as ex:
                resp = {'code:': -1, 'data': str(ex)}
            return resp

        JBoxd.QUEUE.respond(_callback)

    def run(self):
        if VolMgr.has_update_for_user_home_image():
            VolMgr.update_user_home_image(fetch=False)

        while True:
            self.log_debug("JBox daemon waiting for commands...")
            try:
                offline, reply_req = JBoxd.QUEUE.poll(self._is_scheduled(JBoxAsyncJob.CMD_REQ_RESP, ()))
            except ValueError:
                self.log_exception("Exception reading command. Will retry after 10 seconds")
                time.sleep(10)
                continue

            if offline:
                try:
                    self.process_offline()
                except:
                    self.log_exception("Exception scheduling request")

            if reply_req:
                JBoxd.schedule_thread(JBoxAsyncJob.CMD_REQ_RESP, JBoxd.process_and_respond, ())
