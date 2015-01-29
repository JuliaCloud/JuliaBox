import datetime
import pytz
import json
import multiprocessing
import random

import psutil
from cloud.aws import CloudHost

from db import JBoxAccountingV2
from jbox_tasks import JBoxAsyncJob
from jbox_util import LoggerMixin, parse_iso_time
from vol import VolMgr


class JBoxContainer(LoggerMixin):
    CONTAINER_PORT_BINDINGS = {4200: ('127.0.0.1',), 8000: ('127.0.0.1',), 8998: ('127.0.0.1',)}
    DCKR = None
    PINGS = {}
    DCKR_IMAGE = None
    MEM_LIMIT = None

    # By default all groups have 1024 shares.
    # A group with 100 shares will get a ~10% portion of the CPU time (https://wiki.archlinux.org/index.php/Cgroups)
    CPU_LIMIT = 1024
    PORTS = [4200, 8000, 8998]
    VOLUMES = ['/home/juser']
    MAX_CONTAINERS = 0
    VALID_CONTAINERS = {}
    INITIAL_DISK_USED_PCT = None
    LAST_CPU_PCT = None

    ASYNC_JOB = None

    def __init__(self, dockid):
        self.dockid = dockid
        self.props = None
        self.dbgstr = None
        self.host_ports = None

    def refresh(self):
        self.props = None
        self.dbgstr = None
        self.host_ports = None

    def get_props(self):
        if self.props is None:
            self.props = JBoxContainer.DCKR.inspect_container(self.dockid)
        return self.props

    def get_host_ports(self):
        if self.host_ports is None:
            props = self.get_props()
            ports = props['NetworkSettings']['Ports']
            port_map = []
            for port in JBoxContainer.PORTS:
                tcp_port = str(port) + '/tcp'
                port_map.append(ports[tcp_port][0]['HostPort'])
            self.host_ports = tuple(port_map)
        return self.host_ports

    def get_cpu_allocated(self):
        props = self.get_props()
        cpu_shares = props['Config']['CpuShares']
        num_cpus = multiprocessing.cpu_count()
        return max(1, int(num_cpus * cpu_shares / 1024))

    def get_memory_allocated(self):
        props = self.get_props()
        mem = props['Config']['Memory']
        if mem > 0:
            return mem
        return psutil.virtual_memory().total

    def get_disk_allocated(self):
        disk = VolMgr.get_disk_from_container(self.dockid)
        if disk is not None:
            return disk.get_disk_allocated_size()
        return 0

    def debug_str(self):
        if self.dbgstr is None:
            self.dbgstr = "JBoxContainer id=" + str(self.dockid) + ", name=" + str(self.get_name())
        return self.dbgstr

    def get_name(self):
        props = self.get_props()
        return props['Name'] if ('Name' in props) else None

    def get_image_names(self):
        props = self.get_props()
        img_id = props['Image']
        for img in JBoxContainer.DCKR.images():
            if img['Id'] == img_id:
                return img['RepoTags']
        return []

    @staticmethod
    def configure(dckr, image, mem_limit, cpu_limit, max_containers, async_job_ports, async_mode=JBoxAsyncJob.MODE_PUB):
        JBoxContainer.DCKR = dckr
        JBoxContainer.DCKR_IMAGE = image
        JBoxContainer.MEM_LIMIT = mem_limit
        JBoxContainer.CPU_LIMIT = cpu_limit
        JBoxContainer.MAX_CONTAINERS = max_containers
        JBoxContainer.ASYNC_JOB = JBoxAsyncJob(async_job_ports, async_mode)

    @staticmethod
    def _create_new(name):
        jsonobj = JBoxContainer.DCKR.create_container(JBoxContainer.DCKR_IMAGE,
                                                      detach=True,
                                                      mem_limit=JBoxContainer.MEM_LIMIT,
                                                      cpu_shares=JBoxContainer.CPU_LIMIT,
                                                      ports=JBoxContainer.PORTS,
                                                      volumes=JBoxContainer.VOLUMES,
                                                      hostname='juliabox',
                                                      name=name)
        dockid = jsonobj["Id"]
        cont = JBoxContainer(dockid)
        JBoxContainer.log_info("Created %s", cont.debug_str())
        return cont

    @staticmethod
    def async_refresh_disks():
        JBoxContainer.log_info("scheduling refresh of loopback disks")
        JBoxContainer.ASYNC_JOB.send(JBoxAsyncJob.CMD_REFRESH_DISKS, '')

    @staticmethod
    def async_update_user_home_image():
        JBoxContainer.log_info("scheduling update of user home image")
        JBoxContainer.ASYNC_JOB.send(JBoxAsyncJob.CMD_UPDATE_USER_HOME_IMAGE, '')

    @staticmethod
    def async_collect_stats():
        JBoxContainer.log_info("scheduling stats collection")
        JBoxContainer.ASYNC_JOB.send(JBoxAsyncJob.CMD_COLLECT_STATS, '')

    @staticmethod
    def async_update_disk_state():
        JBoxContainer.log_info("updating disk states")
        JBoxContainer.ASYNC_JOB.send(JBoxAsyncJob.CMD_UPDATE_DISK_STATES, '')

    @staticmethod
    def async_schedule_activations():
        JBoxContainer.log_info("scheduling activations")
        JBoxContainer.ASYNC_JOB.send(JBoxAsyncJob.CMD_AUTO_ACTIVATE, '')

    @staticmethod
    def async_launch_by_name(name, email, reuse=True):
        JBoxContainer.log_info("Scheduling startup name:%s email:%s", name, email)
        cname = "/" + name
        if JBoxContainer.VALID_CONTAINERS.has_key(cname):
            del JBoxContainer.VALID_CONTAINERS[cname]
        JBoxContainer.ASYNC_JOB.send(JBoxAsyncJob.CMD_LAUNCH_SESSION, (name, email, reuse))

    def async_backup_and_cleanup(self):
        JBoxContainer.log_info("scheduling cleanup for %s", self.debug_str())
        if self.get_name() in JBoxContainer.VALID_CONTAINERS:
            del JBoxContainer.VALID_CONTAINERS[self.get_name()]
        JBoxContainer.ASYNC_JOB.send(JBoxAsyncJob.CMD_BACKUP_CLEANUP, self.dockid)

    @staticmethod
    def sync_session_status(instance_id):
        JBoxContainer.log_debug("fetching session status from %s", instance_id)
        return JBoxContainer.ASYNC_JOB.sendrecv(JBoxAsyncJob.CMD_SESSION_STATUS, {}, dest=instance_id)

    @staticmethod
    def launch_by_name(name, email, reuse=True):
        JBoxContainer.log_info("Launching container %s", name)

        cont = JBoxContainer.get_by_name(name)

        if (cont is not None) and not reuse:
            cont.delete()
            cont = None

        if cont is None:
            cont = JBoxContainer._create_new(name)

        if not (cont.is_running() or cont.is_restarting()):
            cont.start(email)
        #else:
        #    cont.restart()

        JBoxContainer.publish_container_stats()
        return cont

    @staticmethod
    def publish_container_stats():
        """ Publish custom cloudwatch statistics. Used for status monitoring and auto scaling. """
        nactive = JBoxContainer.num_active()
        CloudHost.publish_stats("NumActiveContainers", "Count", nactive)

        curr_cpu_used_pct = psutil.cpu_percent()
        last_cpu_used_pct = curr_cpu_used_pct if JBoxContainer.LAST_CPU_PCT is None else JBoxContainer.LAST_CPU_PCT
        JBoxContainer.LAST_CPU_PCT = curr_cpu_used_pct
        cpu_used_pct = int((curr_cpu_used_pct + last_cpu_used_pct)/2)

        mem_used_pct = psutil.virtual_memory().percent
        CloudHost.publish_stats("MemUsed", "Percent", mem_used_pct)

        disk_used_pct = 0
        for x in psutil.disk_partitions():
            if not VolMgr.is_mount_path(x.mountpoint):
                try:
                    disk_used_pct = max(psutil.disk_usage(x.mountpoint).percent, disk_used_pct)
                except:
                    pass
        if JBoxContainer.INITIAL_DISK_USED_PCT is None:
            JBoxContainer.INITIAL_DISK_USED_PCT = disk_used_pct
        disk_used_pct = max(0, (disk_used_pct - JBoxContainer.INITIAL_DISK_USED_PCT))
        CloudHost.publish_stats("DiskUsed", "Percent", disk_used_pct)

        cont_load_pct = min(100, max(0, nactive * 100 / JBoxContainer.MAX_CONTAINERS))
        CloudHost.publish_stats("ContainersUsed", "Percent", cont_load_pct)

        CloudHost.publish_stats("DiskIdsUsed", "Percent", VolMgr.used_pct())

        overall_load_pct = max(cont_load_pct, disk_used_pct, mem_used_pct, cpu_used_pct, VolMgr.used_pct())
        CloudHost.publish_stats("Load", "Percent", overall_load_pct)

    @staticmethod
    def maintain(max_timeout=0, inactive_timeout=0, protected_names=()):
        JBoxContainer.log_info("Starting container maintenance...")
        tnow = datetime.datetime.now(pytz.utc)
        tmin = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=pytz.utc)

        stop_before = (tnow - datetime.timedelta(seconds=max_timeout)) if (max_timeout > 0) else tmin
        stop_inacive_before = (tnow - datetime.timedelta(seconds=inactive_timeout)) if (inactive_timeout > 0) else tmin

        all_containers = JBoxContainer.DCKR.containers(all=True)
        all_cnames = {}
        container_id_list = []
        for cdesc in all_containers:
            cid = cdesc['Id']
            cont = JBoxContainer(cid)
            container_id_list.append(cid)
            cname = cont.get_name()
            all_cnames[cname] = cid

            if (cname is None) or (cname in protected_names):
                JBoxContainer.log_debug("Ignoring %s", cont.debug_str())
                continue

            c_is_active = cont.is_running() or cont.is_restarting()
            last_ping = JBoxContainer._get_last_ping(cname)

            # if we don't have a ping record, create one (we must have restarted) 
            if (last_ping is None) and c_is_active:
                JBoxContainer.log_info("Discovered new container %s", cont.debug_str())
                JBoxContainer.record_ping(cname)

            start_time = cont.time_started()
            # check that start time is not absurdly small (indicates a continer that's starting up)
            start_time_not_zero = (tnow-start_time).total_seconds() < (365*24*60*60)
            if (start_time < stop_before) and start_time_not_zero:
                # don't allow running beyond the limit for long running sessions
                # JBoxContainer.log_info("time_started " + str(cont.time_started()) +
                #               " delete_before: " + str(delete_before) +
                #               " cond: " + str(cont.time_started() < delete_before))
                JBoxContainer.log_warn("Running beyond allowed time %s", cont.debug_str())
                cont.async_backup_and_cleanup()
            elif (last_ping is not None) and c_is_active and (last_ping < stop_inacive_before):
                # if inactive for too long, stop it
                # JBoxContainer.log_info("last_ping " + str(last_ping) + " stop_before: " + str(stop_before) +
                #           " cond: " + str(last_ping < stop_before))
                JBoxContainer.log_warn("Inactive beyond allowed time %s", cont.debug_str())
                cont.async_backup_and_cleanup()

        # delete ping entries for non exixtent containers
        for cname in JBoxContainer.PINGS.keys():
            if cname not in all_cnames:
                del JBoxContainer.PINGS[cname]

        JBoxContainer.VALID_CONTAINERS = all_cnames
        JBoxContainer.publish_container_stats()
        VolMgr.refresh_disk_use_status(container_id_list=container_id_list)
        JBoxContainer.log_info("Finished container maintenance.")

    @staticmethod
    def is_valid_container(cname, hostports):
        cont = None
        if cname in JBoxContainer.VALID_CONTAINERS:
            try:
                cont = JBoxContainer(JBoxContainer.VALID_CONTAINERS[cname])
            except:
                pass
        else:
            all_containers = JBoxContainer.DCKR.containers(all=True)
            for cdesc in all_containers:
                cid = cdesc['Id']
                cont = JBoxContainer(cid)
                cont_name = cont.get_name()
                JBoxContainer.VALID_CONTAINERS[cont_name] = cid
                if cname == cont_name:
                    break

        if cont is None:
            return False

        try:
            return hostports == cont.get_host_ports()
        except:
            return False

    def backup_and_cleanup(self):
        self.stop()
        self.delete(backup=True)

    # def backup(self):
    #     JBoxContainer.log_info("Backing up %s", self.debug_str())
    #     disk = VolMgr.get_disk_from_container(self.dockid)
    #     if disk is not None:
    #         disk.backup()

    @staticmethod
    def num_active():
        active_containers = JBoxContainer.DCKR.containers(all=False)
        return len(active_containers)

    @staticmethod
    def num_stopped():
        all_containers = JBoxContainer.DCKR.containers(all=True)
        return len(all_containers) - JBoxContainer.num_active()

    @staticmethod
    def get_by_name(name):
        nname = "/" + unicode(name)

        for c in JBoxContainer.DCKR.containers(all=True):
            if ('Names' in c) and (c['Names'] is not None) and (c['Names'][0] == nname):
                return JBoxContainer(c['Id'])
        return None

    @staticmethod
    def record_ping(name):
        JBoxContainer.PINGS[name] = datetime.datetime.now(pytz.utc)
        # log_info("Recorded ping for %s", name)

    @staticmethod
    def _get_last_ping(name):
        return JBoxContainer.PINGS[name] if (name in JBoxContainer.PINGS) else None

    def is_running(self):
        props = self.get_props()
        state = props['State']
        return state['Running'] if 'Running' in state else False

    def is_restarting(self):
        props = self.get_props()
        state = props['State']
        return state['Restarting'] if 'Restarting' in state else False

    def time_started(self):
        props = self.get_props()
        return parse_iso_time(props['State']['StartedAt'])

    def time_finished(self):
        props = self.get_props()
        return parse_iso_time(props['State']['FinishedAt'])

    def time_created(self):
        props = self.get_props()
        return parse_iso_time(props['Created'])

    def stop(self):
        JBoxContainer.log_info("Stopping %s", self.debug_str())
        self.refresh()
        if self.is_running():
            JBoxContainer.DCKR.stop(self.dockid, timeout=5)
            self.refresh()
            JBoxContainer.log_info("Stopped %s", self.debug_str())
            self.record_usage()
        else:
            JBoxContainer.log_info("Already stopped or restarting %s", self.debug_str())

    def start(self, email):
        self.refresh()
        JBoxContainer.log_info("Starting %s", self.debug_str())
        if self.is_running() or self.is_restarting():
            JBoxContainer.log_warn("Already started %s. Browser connectivity issues?", self.debug_str())
            return

        disk = VolMgr.get_disk_for_user(email)
        vols = {
            disk.disk_path: {
                'bind': JBoxContainer.VOLUMES[0],
                'ro': False
            }
        }

        JBoxContainer.DCKR.start(self.dockid, port_bindings=JBoxContainer.CONTAINER_PORT_BINDINGS, binds=vols)
        self.refresh()
        JBoxContainer.log_info("Started %s", self.debug_str())
        cname = self.get_name()
        if cname is not None:
            JBoxContainer.record_ping(cname)

    def restart(self):
        self.refresh()
        JBoxContainer.log_info("Restarting %s", self.debug_str())
        JBoxContainer.DCKR.restart(self.dockid, timeout=5)
        self.refresh()
        JBoxContainer.log_info("Restarted %s", self.debug_str())
        cname = self.get_name()
        if cname is not None:
            JBoxContainer.record_ping(cname)

    def kill(self):
        JBoxContainer.log_info("Killing %s", self.debug_str())
        JBoxContainer.DCKR.kill(self.dockid)
        self.refresh()
        JBoxContainer.log_info("Killed %s", self.debug_str())
        self.record_usage()

    def delete(self, backup=False):
        JBoxContainer.log_info("Deleting %s", self.debug_str())
        self.refresh()
        cname = self.get_name()
        if self.is_running() or self.is_restarting():
            self.kill()

        disk = VolMgr.get_disk_from_container(self.dockid)
        if disk is not None:
            disk.release(backup=backup)

        if cname is not None:
            JBoxContainer.PINGS.pop(cname, None)
        JBoxContainer.DCKR.remove_container(self.dockid)
        JBoxContainer.log_info("Deleted %s", self.debug_str())

    def record_usage(self):
        for retry in range(1, 10):
            try:
                start_time = self.time_created()
                finish_time = self.time_finished()
                if retry > 1:
                    finish_time += datetime.timedelta(microseconds=random.randint(1, 100))
                acct = JBoxAccountingV2(self.get_name(), json.dumps(self.get_image_names()),
                                        start_time, stop_time=finish_time)
                acct.save()
                break
            except:
                if retry == 10:
                    self.log_exception("error recording usage")
                else:
                    self.log_warn("error recording usage, shall retry.")