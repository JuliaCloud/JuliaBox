import threading
import json
import time
import signal
# import os
import sys
import psutil

from cloud import JBPluginCloud
from cloud import Compute
import db
from db import JBoxUserV2, JBoxDynConfig, is_proposed_cluster_leader
from jbox_tasks import JBoxAsyncJob, JBPluginTask
from jbox_util import LoggerMixin, JBoxCfg, retry
from juliabox.interactive import SessContainer
from api import APIContainer
from jbox_container import BaseContainer
from vol import VolMgr


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
    shutdown = False

    ACTIVE = {}
    LOCK = threading.Lock()
    MAX_AUTO_ACTIVATIONS_PER_RUN = 10
    MAX_ACTIVATIONS_PER_SEC = 10
    ACTIVATION_SUBJECT = None
    ACTIVATION_BODY = None
    ACTIVATION_SENDER = None
    QUEUE = None

    def __init__(self):
        LoggerMixin.configure()
        db.configure()
        Compute.configure()
        SessContainer.configure()
        APIContainer.configure()
        VolMgr.configure()

        JBoxAsyncJob.configure()
        JBoxAsyncJob.init(JBoxAsyncJob.MODE_SUB)

        self.log_debug("Container manager listening on ports: %s", repr(JBoxCfg.get('container_manager_ports')))
        JBoxd.QUEUE = JBoxAsyncJob.get()

        JBoxd.MAX_ACTIVATIONS_PER_SEC = JBoxCfg.get('user_activation.max_activations_per_sec')
        JBoxd.MAX_AUTO_ACTIVATIONS_PER_RUN = JBoxCfg.get('user_activation.max_activations_per_run')
        JBoxd.ACTIVATION_SUBJECT = JBoxCfg.get('user_activation.mail_subject')
        JBoxd.ACTIVATION_BODY = JBoxCfg.get('user_activation.mail_body')
        JBoxd.ACTIVATION_SENDER = JBoxCfg.get('user_activation.sender')

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
        cont = SessContainer(dockid)
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
        cont = SessContainer.get_by_name(sessname)
        if (cont is not None) and JBoxd._is_scheduled(JBoxAsyncJob.CMD_BACKUP_CLEANUP, (cont.dockid,)):
            JBoxd.log_debug("Waiting for backup of session %s", sessname)
            return False
        return True

    @staticmethod
    @jboxd_method
    def launch_session(name, email, reuse=True):
        JBoxd._wait_for_session_backup(name)
        VolMgr.refresh_disk_use_status()
        SessContainer.launch_by_name(name, email, reuse=reuse)
        JBoxd.publish_perf_counters()

    @staticmethod
    @jboxd_method
    def auto_activate():
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_SENDMAIL)
        if plugin is None:
            JBoxd.log_error("No plugin found for sending mails. Can not auto activate users.")
            return

        num_mails_24h, rate = plugin.get_email_rates()
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
            plugin.send_email(user_id, JBoxd.ACTIVATION_SENDER, JBoxd.ACTIVATION_SUBJECT, JBoxd.ACTIVATION_BODY)

            # set user as activated
            user = JBoxUserV2(user_id)
            user.set_activation_state(JBoxUserV2.ACTIVATION_CODE_AUTO, JBoxUserV2.ACTIVATION_GRANTED)
            user.save()

            rate_per_second -= 1
            if rate_per_second <= 0:
                rate_per_second = min(JBoxd.MAX_ACTIVATIONS_PER_SEC, rate)
                time.sleep(1)

    @staticmethod
    @jboxd_method
    def update_user_home_image():
        VolMgr.update_user_home_image(fetch=True)
        VolMgr.refresh_user_home_image()

    @staticmethod
    @jboxd_method
    def refresh_disks():
        if JBoxd._is_scheduled(JBoxAsyncJob.CMD_UPDATE_USER_HOME_IMAGE, ()):
            return
        VolMgr.refresh_user_home_image()

    @staticmethod
    @jboxd_method
    def collect_stats():
        VolMgr.publish_stats()
        db.publish_stats()
        JBoxDynConfig.set_stat_collected_date(Compute.get_install_id())

    @staticmethod
    @jboxd_method
    def publish_container_stats():
        VolMgr.publish_stats()
        db.publish_stats()
        JBoxDynConfig.set_stat_collected_date(Compute.get_install_id())

    @staticmethod
    def publish_perf_counters():
        """ Publish performance counters. Used for status monitoring and auto scaling. """
        VolMgr.refresh_disk_use_status()
        
        nactive = BaseContainer.num_active(BaseContainer.SFX_INT)
        Compute.publish_stats("NumActiveContainers", "Count", nactive)

        nactive_api = BaseContainer.num_active(BaseContainer.SFX_API)
        Compute.publish_stats("NumActiveAPIContainers", "Count", nactive_api)

        curr_cpu_used_pct = psutil.cpu_percent()
        last_cpu_used_pct = curr_cpu_used_pct if BaseContainer.LAST_CPU_PCT is None else BaseContainer.LAST_CPU_PCT
        BaseContainer.LAST_CPU_PCT = curr_cpu_used_pct
        cpu_used_pct = int((curr_cpu_used_pct + last_cpu_used_pct)/2)
        Compute.publish_stats("CPUUsed", "Percent", cpu_used_pct)

        mem_used_pct = psutil.virtual_memory().percent
        Compute.publish_stats("MemUsed", "Percent", mem_used_pct)

        disk_used_pct = 0
        for x in psutil.disk_partitions():
            if not VolMgr.is_mount_path(x.mountpoint):
                try:
                    disk_used_pct = max(psutil.disk_usage(x.mountpoint).percent, disk_used_pct)
                except:
                    pass
        if BaseContainer.INITIAL_DISK_USED_PCT is None:
            BaseContainer.INITIAL_DISK_USED_PCT = disk_used_pct
        disk_used_pct = max(0, (disk_used_pct - BaseContainer.INITIAL_DISK_USED_PCT))
        Compute.publish_stats("DiskUsed", "Percent", disk_used_pct)

        cont_load_pct = min(100, max(0, nactive * 100 / SessContainer.MAX_CONTAINERS))
        Compute.publish_stats("ContainersUsed", "Percent", cont_load_pct)

        api_cont_load_pct = min(100, max(0, nactive_api * 100 / APIContainer.MAX_CONTAINERS))
        Compute.publish_stats("APIContainersUsed", "Percent", api_cont_load_pct)

        Compute.publish_stats("DiskIdsUsed", "Percent", VolMgr.used_pct())

        overall_load_pct = max(cont_load_pct, api_cont_load_pct, disk_used_pct, mem_used_pct, cpu_used_pct, VolMgr.used_pct())
        Compute.publish_stats("Load", "Percent", overall_load_pct)

    @staticmethod
    def schedule_housekeeping(cmd, is_leader):
        JBoxd.publish_perf_counters()
        features = [JBPluginTask.JBP_NODE]
        if is_leader is True:
            features.append(JBPluginTask.JBP_CLUSTER)

        for feature in features:
            for plugin in JBPluginTask.jbox_get_plugins(feature):
                JBoxd.schedule_thread(cmd, plugin.do_periodic_task, (feature,))

    @staticmethod
    @jboxd_method
    def plugin_action(plugin_type, plugin_class, data):
        matching_plugin = None
        for plugin in JBPluginTask.jbox_get_plugins(plugin_type):
            if plugin_class is None:
                matching_plugin = plugin
                break
            elif plugin_class == plugin.__name__:
                matching_plugin = plugin
                break
        if matching_plugin is not None:
            matching_plugin.do_task(plugin_type, data)

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
        elif cmd == JBoxAsyncJob.CMD_PLUGIN_MAINTENANCE:
            JBoxd.schedule_housekeeping(cmd, data)
            return
        elif cmd == JBoxAsyncJob.CMD_PLUGIN_TASK:
            args = (data[0], data[1], data[2])
            fn = JBoxd.plugin_action
        else:
            self.log_error("Unknown command " + str(cmd))
            return

        JBoxd.schedule_thread(cmd, fn, args)

    @staticmethod
    def get_session_status():
        ret = {}
        for c in BaseContainer.session_containers(allcontainers=True):
            name = c["Names"][0] if (("Names" in c) and (c["Names"] is not None)) else c["Id"][0:12]
            ret[name] = c["Status"]

        return ret

    @staticmethod
    def get_api_status():
        api_status = dict()
        for c in BaseContainer.api_containers(allcontainers=True):
            name = c["Names"][0] if (("Names" in c) and (c["Names"] is not None)) else c["Id"][0:12]
            api_name = APIContainer.get_api_name_from_container_name(name)
            if api_name is None:
                continue
            cnt = api_status.get(api_name, 0)
            api_status[api_name] = cnt + 1
        self_load = Compute.get_instance_stats(Compute.get_instance_id(), 'Load')
        accept = Compute.should_accept_session(is_proposed_cluster_leader())

        return {'load': self_load, 'accept': accept, 'api_status': api_status}

    @staticmethod
    def is_terminating():
        if not JBoxCfg.get('cloud_host.scale_down'):
            return False

        num_active = BaseContainer.num_active()
        terminate = (num_active == 0) and Compute.can_terminate(is_proposed_cluster_leader())

        if terminate:
            JBoxd.log_warn("terminating to scale down")
            try:
                Compute.deregister_instance_dns()
            except:
                JBoxd.log_error("Error deregistering instance dns")
            Compute.terminate_instance()

        return terminate

    @staticmethod
    @jboxd_method
    def process_and_respond():
        def _callback(cmd, data):
            try:
                if cmd == JBoxAsyncJob.CMD_SESSION_STATUS:
                    resp = {'code': 0, 'data': JBoxd.get_session_status()}
                elif cmd == JBoxAsyncJob.CMD_API_STATUS:
                    resp = {'code': 0, 'data': JBoxd.get_api_status()}
                elif cmd == JBoxAsyncJob.CMD_IS_TERMINATING:
                    resp = {'code': 0, 'data': JBoxd.is_terminating()}
                else:
                    resp = {'code:': -2, 'data': ('unknown command %s' % (repr(cmd,)))}
            except Exception as ex:
                resp = {'code:': -1, 'data': str(ex)}
            return resp

        JBoxd.QUEUE.respond(_callback)

    @staticmethod
    def signal_handler(signum, frame):
        JBoxd.shutdown = True
        JBoxd.log_info("Received signal %r. Shutting down.", signum)
        sys.exit(0)
        # os._exit(0)

    def run(self):
        Compute.deregister_instance_dns()
        Compute.register_instance_dns()
        JBoxd.publish_perf_counters()

        JBoxd.log_debug("Setting up signal handlers")
        signal.signal(signal.SIGINT, JBoxd.signal_handler)
        signal.signal(signal.SIGTERM, JBoxd.signal_handler)

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
