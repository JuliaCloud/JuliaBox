import os
import time
import datetime
import pytz
import tarfile
import json
import multiprocessing

import isodate
import psutil

from db.accounting_v2 import JBoxAccountingV2
from jbox_util import LoggerMixin, CloudHelper, ensure_delete
from jbox_crypto import ssh_keygen


class JBoxContainer(LoggerMixin):
    CONTAINER_PORT_BINDINGS = {4200: ('127.0.0.1',), 8000: ('127.0.0.1',), 8998: ('127.0.0.1',)}
    HOST_VOLUMES = None
    DCKR = None
    PINGS = {}
    DCKR_IMAGE = None
    MEM_LIMIT = None

    # By default all groups have 1024 shares.
    # A group with 100 shares will get a ~10% portion of the CPU time (https://wiki.archlinux.org/index.php/Cgroups)
    CPU_LIMIT = 1024
    PORTS = [4200, 8000, 8998]
    VOLUMES = ['/home/juser']
    LOCAL_TZ_OFFSET = 0
    FS_LOC = None
    USER_HOME_IMG = None
    BACKUP_LOC = None
    DISK_LIMIT = None
    BACKUP_BUCKET = None
    MAX_CONTAINERS = 0
    MAX_DISKS = 0
    VALID_CONTAINERS = {}
    DISK_USE_STATUS = {}
    INITIAL_DISK_USED_PCT = None
    LAST_CPU_PCT = None

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

    def get_disk_ids_used(self):
        used = []
        try:
            props = self.get_props()
            vols = props['Volumes']
            for _cpath, hpath in vols.iteritems():
                if hpath.startswith(JBoxContainer.FS_LOC):
                    used.append(int(hpath.split('/')[-1]))
        except:
            self.log_error("error finding disk ids used in " + self.debug_str())
            return []
        return used

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

    @classmethod
    def get_disk_allocated(cls):
        return JBoxContainer.DISK_LIMIT

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
    def configure(dckr, image, mem_limit, cpu_limit, disk_limit, host_volumes, fs_loc, backup_loc, user_home_img,
                  max_containers, max_disks, backup_bucket=None):
        JBoxContainer.DCKR = dckr
        JBoxContainer.DCKR_IMAGE = image
        JBoxContainer.MEM_LIMIT = mem_limit
        JBoxContainer.CPU_LIMIT = cpu_limit
        JBoxContainer.LOCAL_TZ_OFFSET = JBoxContainer.local_time_offset()
        JBoxContainer.HOST_VOLUMES = host_volumes
        JBoxContainer.FS_LOC = fs_loc
        JBoxContainer.USER_HOME_IMG = user_home_img
        JBoxContainer.BACKUP_LOC = backup_loc
        JBoxContainer.DISK_LIMIT = disk_limit
        JBoxContainer.BACKUP_BUCKET = backup_bucket
        JBoxContainer.MAX_CONTAINERS = max_containers
        JBoxContainer.MAX_DISKS = max_disks
        JBoxContainer.refresh_disk_use_status()

    @staticmethod
    def refresh_disk_use_status(container_id_list=None, container_obj_list=None):
        for idx in range(0, JBoxContainer.MAX_DISKS):
            JBoxContainer.DISK_USE_STATUS[idx] = False

        if container_obj_list is None:
            container_obj_list = []

            if container_id_list is None:
                container_id_list = JBoxContainer.DCKR.containers(all=True)

            for cdesc in container_id_list:
                cid = cdesc['Id']
                cont = JBoxContainer(cid)
                container_obj_list.append(cont)

        nfree = JBoxContainer.MAX_DISKS
        for cont in container_obj_list:
            for disk_id in cont.get_disk_ids_used():
                JBoxContainer.DISK_USE_STATUS[disk_id] = True
                nfree -= 1
        JBoxContainer.log_info("Disk free: " + str(nfree) + "/" + str(JBoxContainer.MAX_DISKS))

    @staticmethod
    def disk_ids_used_pct():
        pct = (sum(JBoxContainer.DISK_USE_STATUS.values()) * 100) / len(JBoxContainer.DISK_USE_STATUS)
        return min(100, max(0, pct))

    @staticmethod
    def get_unused_disk_id():
        for idx in range(0, JBoxContainer.MAX_DISKS):
            if not JBoxContainer.DISK_USE_STATUS[idx]:
                return idx
        return -1

    @staticmethod
    def mark_disk_used(idx, used=True):
        JBoxContainer.DISK_USE_STATUS[idx] = used

    @staticmethod
    def create_new(name):
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
        JBoxContainer.log_info("Created " + cont.debug_str())
        # cont.create_restore_file()
        return cont

    @staticmethod
    def launch_by_name(name, reuse=True):
        JBoxContainer.log_info("Launching container: " + name)

        cont = JBoxContainer.get_by_name(name)

        if (cont is not None) and not reuse:
            cont.delete()
            cont = None

        if cont is None:
            cont = JBoxContainer.create_new(name)

        if not (cont.is_running() or cont.is_restarting()):
            cont.start()
        else:
            cont.restart()

        JBoxContainer.publish_container_stats()
        return cont

    @staticmethod
    def publish_container_stats():
        """ Publish custom cloudwatch statistics. Used for status monitoring and auto scaling. """
        nactive = JBoxContainer.num_active()
        CloudHelper.publish_stats("NumActiveContainers", "Count", nactive)

        curr_cpu_used_pct = psutil.cpu_percent()
        last_cpu_used_pct = curr_cpu_used_pct if JBoxContainer.LAST_CPU_PCT is None else JBoxContainer.LAST_CPU_PCT
        JBoxContainer.LAST_CPU_PCT = curr_cpu_used_pct
        cpu_used_pct = int((curr_cpu_used_pct + last_cpu_used_pct)/2)

        mem_used_pct = psutil.virtual_memory().percent
        CloudHelper.publish_stats("MemUsed", "Percent", mem_used_pct)

        disk_used_pct = 0
        for x in psutil.disk_partitions():
            if x.mountpoint.startswith(JBoxContainer.FS_LOC):
                continue
            try:
                disk_used_pct = max(psutil.disk_usage(x.mountpoint).percent, disk_used_pct)
            except:
                pass
        if JBoxContainer.INITIAL_DISK_USED_PCT is None:
            JBoxContainer.INITIAL_DISK_USED_PCT = disk_used_pct
        disk_used_pct = max(0, (disk_used_pct - JBoxContainer.INITIAL_DISK_USED_PCT))
        CloudHelper.publish_stats("DiskUsed", "Percent", disk_used_pct)

        cont_load_pct = min(100, max(0, nactive * 100 / JBoxContainer.MAX_CONTAINERS))
        CloudHelper.publish_stats("ContainersUsed", "Percent", cont_load_pct)

        disk_ids_used_pct = JBoxContainer.disk_ids_used_pct()
        CloudHelper.publish_stats("DiskIdsUsed", "Percent", disk_ids_used_pct)

        overall_load_pct = max(cont_load_pct, disk_used_pct, mem_used_pct, cpu_used_pct, disk_ids_used_pct)
        CloudHelper.publish_stats("Load", "Percent", overall_load_pct)

    @staticmethod
    def maintain(max_timeout=0, inactive_timeout=0, protected_names=()):
        JBoxContainer.log_info("Starting container maintenance...")
        tnow = datetime.datetime.now(pytz.utc)
        tmin = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=pytz.utc)

        stop_before = (tnow - datetime.timedelta(seconds=max_timeout)) if (max_timeout > 0) else tmin
        stop_inacive_before = (tnow - datetime.timedelta(seconds=inactive_timeout)) if (inactive_timeout > 0) else tmin

        all_containers = JBoxContainer.DCKR.containers(all=True)
        all_cnames = {}
        container_obj_list = []
        for cdesc in all_containers:
            cid = cdesc['Id']
            cont = JBoxContainer(cid)
            container_obj_list.append(cont)
            cname = cont.get_name()
            all_cnames[cname] = cid

            if (cname is None) or (cname in protected_names):
                JBoxContainer.log_debug("Ignoring " + cont.debug_str())
                continue

            c_is_active = cont.is_running() or cont.is_restarting()
            last_ping = JBoxContainer.get_last_ping(cname)

            # if we don't have a ping record, create one (we must have restarted) 
            if (last_ping is None) and c_is_active:
                JBoxContainer.log_info("Discovered new container " + cont.debug_str())
                JBoxContainer.record_ping(cname)

            if cont.time_started() < stop_before:
                # don't allow running beyond the limit for long running sessions
                # JBoxContainer.log_info("time_started " + str(cont.time_started()) +
                #               " delete_before: " + str(delete_before) +
                #               " cond: " + str(cont.time_started() < delete_before))
                JBoxContainer.log_info("Running beyond allowed time " + cont.debug_str())
                cont.stop()
            elif (last_ping is not None) and c_is_active and (last_ping < stop_inacive_before):
                # if inactive for too long, stop it
                # JBoxContainer.log_info("last_ping " + str(last_ping) + " stop_before: " + str(stop_before) +
                #           " cond: " + str(last_ping < stop_before))
                JBoxContainer.log_info("Inactive beyond allowed time " + cont.debug_str())
                cont.stop()

        # delete ping entries for non exixtent containers
        for cname in JBoxContainer.PINGS.keys():
            if cname not in all_cnames:
                del JBoxContainer.PINGS[cname]

        JBoxContainer.VALID_CONTAINERS = all_cnames
        JBoxContainer.publish_container_stats()
        JBoxContainer.refresh_disk_use_status(container_obj_list=container_obj_list)
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

    @staticmethod
    def pull_from_s3(local_file, metadata_only=False):
        if JBoxContainer.BACKUP_BUCKET is None:
            return None
        return CloudHelper.pull_file_from_s3(JBoxContainer.BACKUP_BUCKET, local_file, metadata_only=metadata_only)

    @staticmethod
    def backup_and_cleanup(delete_stopped_timeout):
        JBoxContainer.log_info("Starting container backup...")
        tnow = datetime.datetime.now(pytz.utc)
        tmin = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=pytz.utc)

        delete_stopped_before = tnow - datetime.timedelta(seconds=delete_stopped_timeout) if \
            (delete_stopped_timeout > 0) else tmin

        all_containers = JBoxContainer.DCKR.containers(all=True)
        for cdesc in all_containers:
            cont = JBoxContainer(cdesc['Id'])
            c_is_active = cont.is_running() or cont.is_restarting()
            fin_time = cont.time_finished()
            # check that finish time is not absurdly small (indicates a continer that's starting up)
            fin_time_not_zero = (tnow-fin_time).total_seconds() < (365*24*60*60)
            if (not c_is_active) and fin_time_not_zero and (fin_time < delete_stopped_before):
                cont.backup()
                cont.delete()
        JBoxContainer.log_info("Finished container backup.")

    def backup(self):
        JBoxContainer.log_info("Backing up " + self.debug_str() + " at " + str(JBoxContainer.BACKUP_LOC))
        cname = self.get_name()
        if cname is None:
            return

        bkup_file = os.path.join(JBoxContainer.BACKUP_LOC, cname[1:] + ".tar.gz")

        if not (self.is_running() or self.is_restarting()):
            k = JBoxContainer.pull_from_s3(bkup_file, True)
            bkup_file_mtime = None
            if k is not None:
                bkup_file_mtime = JBoxContainer.parse_iso_time(k.get_metadata('backup_time'))
            elif os.path.exists(bkup_file):
                bkup_file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(bkup_file), pytz.utc) + \
                                  datetime.timedelta(seconds=JBoxContainer.LOCAL_TZ_OFFSET)

            if bkup_file_mtime is not None:
                tstart = self.time_started()
                tstop = self.time_finished()
                tcomp = tstart if ((tstop is None) or (tstart > tstop)) else tstop
                if tcomp <= bkup_file_mtime:
                    JBoxContainer.log_info("Already backed up " + self.debug_str())
                    return

        disk_ids_used = self.get_disk_ids_used()
        if len(disk_ids_used) > 0:
            if len(disk_ids_used) > 1:
                JBoxContainer.log_info("Can not backup more than one disks per user yet. Backing up the first disk.")
        elif len(disk_ids_used) == 0:
            JBoxContainer.log_info("No disks to backup")
            return

        disk_id_used = disk_ids_used[0]
        disk_path = os.path.join(JBoxContainer.FS_LOC, str(disk_id_used))
        bkup_tar = tarfile.open(bkup_file, 'w:gz')

        for f in os.listdir(disk_path):
            if f.startswith('.') and (f in ['.julia', '.ipython']):
                continue
            full_path = os.path.join(disk_path, f)
            bkup_tar.add(full_path, os.path.join('juser', f))
        bkup_tar.close()
        os.chmod(bkup_file, 0666)
        ensure_delete(disk_path)

        # Upload to S3 if so configured. Delete from local if successful.
        bkup_file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(bkup_file), pytz.utc) + datetime.timedelta(
            seconds=JBoxContainer.LOCAL_TZ_OFFSET)
        if JBoxContainer.BACKUP_BUCKET is not None:
            if CloudHelper.push_file_to_s3(JBoxContainer.BACKUP_BUCKET, bkup_file,
                                            metadata={'backup_time': bkup_file_mtime.isoformat()}) is not None:
                os.remove(bkup_file)
                JBoxContainer.log_info("Moved backup to S3 " + self.debug_str())

    @staticmethod
    def create_disk():
        disk_id = JBoxContainer.get_unused_disk_id()
        if disk_id < 0:
            raise Exception("No free disk available")
        disk_path = os.path.join(JBoxContainer.FS_LOC, str(disk_id))
        ensure_delete(disk_path)
        JBoxContainer.restore_user_home(disk_path)
        JBoxContainer.setup_instance_config(disk_path)
        return disk_id, disk_path

    @staticmethod
    def restore_user_home(disk_path):
        user_home = tarfile.open(JBoxContainer.USER_HOME_IMG, 'r:gz')
        user_home.extractall(disk_path)
        user_home.close()

    @staticmethod
    def setup_instance_config(disk_path):
        nbconfig = os.path.join(disk_path, '.ipython/profile_julia/ipython_notebook_config.py')
        with open(nbconfig, "a") as nbconfig_file:
            nbconfig_file.write(
                "c.NotebookApp.websocket_url = 'ws://" + CloudHelper.instance_public_hostname() + "'\n")

    def restore_backup_to_disk(self, disk_path):
        cname = self.get_name()
        if cname is None:
            raise Exception("Could not get container name")

        src = os.path.join(JBoxContainer.BACKUP_LOC, cname[1:] + ".tar.gz")
        k = JBoxContainer.pull_from_s3(src)  # download from S3 if exists
        if not os.path.exists(src):
            return
        JBoxContainer.log_info("Filtering out restore info from backup " + src + " to " + disk_path)

        src_tar = tarfile.open(src, 'r:gz')
        for info in src_tar.getmembers():
            if not info.name.startswith('juser/'):
                continue
            if info.name.startswith('juser/.') and (info.name.split('/')[1] in ['.juliabox', '.julia', '.ipython']):
                continue
            info.name = info.name[6:]
            if len(info.name) == 0:
                continue
            src_tar.extract(info, disk_path)
        src_tar.close()
        JBoxContainer.log_info("Restored backup at " + disk_path)
        # delete local copy of backup if we have it on s3
        if k is not None:
            os.remove(src)

    @staticmethod
    def gen_ssh_key(disk_path):
        ssh_path = os.path.join(disk_path, '.ssh')
        ssh_key_path = os.path.join(ssh_path, 'id_rsa')
        ssh_pub_key_path = os.path.join(ssh_path, 'id_rsa.pub')

        if not os.path.exists(ssh_path):
            os.mkdir(ssh_path)
            os.chmod(ssh_path, 0700)

        if os.path.exists(ssh_key_path) and os.path.exists(ssh_pub_key_path):
            return
        if os.path.exists(ssh_key_path) and not os.access(ssh_key_path, os.W_OK):
            os.chmod(ssh_key_path, 0600)
        if os.path.exists(ssh_pub_key_path) and not os.access(ssh_pub_key_path, os.W_OK):
            os.chmod(ssh_key_path, 0644)

        public_key, private_key = ssh_keygen()
        public_key += " juliabox\n"
        private_key += "\n"
        with open(ssh_key_path, 'w') as f:
            f.write(private_key)
        with open(ssh_pub_key_path, 'w') as f:
            f.write(public_key)
        os.chmod(ssh_key_path, 0600)
        os.chmod(ssh_pub_key_path, 0644)

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
        # log_info("Recorded ping for " + name)

    @staticmethod
    def get_last_ping(name):
        return JBoxContainer.PINGS[name] if (name in JBoxContainer.PINGS) else None

    @staticmethod
    def parse_iso_time(tm):
        if tm is not None:
            tm = isodate.parse_datetime(tm)
        return tm

    @staticmethod
    def local_time_offset():
        """Return offset of local zone from GMT"""
        if time.localtime().tm_isdst and time.daylight:
            return time.altzone
        else:
            return time.timezone

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
        return JBoxContainer.parse_iso_time(props['State']['StartedAt'])

    def time_finished(self):
        props = self.get_props()
        return JBoxContainer.parse_iso_time(props['State']['FinishedAt'])

    def time_created(self):
        props = self.get_props()
        return JBoxContainer.parse_iso_time(props['Created'])

    def stop(self):
        JBoxContainer.log_info("Stopping " + self.debug_str())
        self.refresh()
        if self.is_running():
            JBoxContainer.DCKR.stop(self.dockid, timeout=5)
            self.refresh()
            JBoxContainer.log_info("Stopped " + self.debug_str())
            self.record_usage()
        else:
            JBoxContainer.log_info("Already stopped or restarting" + self.debug_str())

    def get_host_volume(self, hvol, disk_id):
        hvol = hvol.replace('${CNAME}', self.get_name())
        hvol = hvol.replace('${DISK_ID}', str(disk_id))
        return hvol

    def start(self):
        self.refresh()
        JBoxContainer.log_info("Starting " + self.debug_str())
        if self.is_running() or self.is_restarting():
            JBoxContainer.log_info("Already started " + self.debug_str())
            return

        disk_id, disk_path = JBoxContainer.create_disk()
        self.restore_backup_to_disk(disk_path)
        JBoxContainer.gen_ssh_key(disk_path)
        JBoxContainer.mark_disk_used(disk_id)

        vols = {}
        for hvol, cvol in zip(JBoxContainer.HOST_VOLUMES, JBoxContainer.VOLUMES):
            hvol = self.get_host_volume(hvol, disk_id)
            vols[hvol] = {'bind': cvol, 'ro': False}

        JBoxContainer.DCKR.start(self.dockid, port_bindings=JBoxContainer.CONTAINER_PORT_BINDINGS, binds=vols)
        self.refresh()
        JBoxContainer.log_info("Started " + self.debug_str())
        cname = self.get_name()
        if cname is not None:
            JBoxContainer.record_ping(cname)

    def restart(self):
        self.refresh()
        JBoxContainer.log_info("Restarting " + self.debug_str())
        JBoxContainer.DCKR.restart(self.dockid, timeout=5)
        self.refresh()
        JBoxContainer.log_info("Restarted " + self.debug_str())
        cname = self.get_name()
        if cname is not None:
            JBoxContainer.record_ping(cname)

    def kill(self):
        JBoxContainer.log_info("Killing " + self.debug_str())
        JBoxContainer.DCKR.kill(self.dockid)
        self.refresh()
        JBoxContainer.log_info("Killed " + self.debug_str())
        self.record_usage()

    def delete(self):
        JBoxContainer.log_info("Deleting " + self.debug_str())
        self.refresh()
        cname = self.get_name()
        if self.is_running() or self.is_restarting():
            self.kill()

        JBoxContainer.DCKR.remove_container(self.dockid)
        if cname is not None:
            JBoxContainer.PINGS.pop(cname, None)
        JBoxContainer.log_info("Deleted " + self.debug_str())

    def record_usage(self):
        start_time = self.time_created()
        finish_time = self.time_finished()
        acct = JBoxAccountingV2(self.get_name(), json.dumps(self.get_image_names()),
                                start_time, stop_time=finish_time)
        acct.save()
