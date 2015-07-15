import os
import threading
import time

from juliabox.cloud.aws import CloudHost
from juliabox.db import JBoxSessionProps
from juliabox.jbox_util import unique_sessname, JBoxCfg
from juliabox.vol import JBoxVol
from disk_state_tbl import JBoxDiskState
from juliabox.jbox_container import JBoxContainer


class JBoxEBSVol(JBoxVol):
    provides = [JBoxVol.PLUGIN_USERHOME, JBoxVol.PLUGIN_EBS_USERHOME]

    DEVICES = []
    MAX_DISKS = 0
    FS_LOC = None
    DISK_LIMIT = None
    DISK_USE_STATUS = {}
    DISK_RESERVE_TIME = {}
    DISK_TEMPLATE_SNAPSHOT = None
    LOCK = None

    @staticmethod
    def configure():
        num_disks_max = JBoxCfg.get('numdisksmax')
        JBoxEBSVol.FS_LOC = os.path.expanduser(JBoxCfg.get('cloud_host.ebs_mnt_location'))
        JBoxEBSVol.DISK_LIMIT = 1
        JBoxEBSVol.MAX_DISKS = num_disks_max
        JBoxEBSVol.DISK_TEMPLATE_SNAPSHOT = JBoxCfg.get('cloud_host.ebs_template')

        JBoxEBSVol.DEVICES = JBoxEBSVol._get_configured_devices(JBoxEBSVol.FS_LOC)
        if len(JBoxEBSVol.DEVICES) < num_disks_max:
            raise Exception("Not enough EBS mount points configured")

        JBoxEBSVol.LOCK = threading.Lock()
        JBoxEBSVol.refresh_disk_use_status()

    @classmethod
    def get_disk_allocated_size(cls):
        return JBoxEBSVol.DISK_LIMIT * 1000000000

    @staticmethod
    def _id_from_device(dev_path):
        return dev_path.split('/')[-1]

    @staticmethod
    def _get_configured_devices(fs_loc):
        devices = []
        with open('/etc/fstab', 'r') as fstab:
            for line in fstab:
                line = line.strip()
                if (len(line) == 0) or line.startswith('#'):
                    continue
                comps = line.split()
                if (len(comps) == 6) and comps[1].startswith(fs_loc):
                    device = comps[0]
                    devices.append(JBoxEBSVol._id_from_device(device))
        return devices

    @staticmethod
    def _get_disk_ids_used(cid):
        used = []
        props = JBoxEBSVol.dckr().inspect_container(cid)
        try:
            vols = props['Volumes']
            for _cpath, hpath in vols.iteritems():
                if hpath.startswith(JBoxEBSVol.FS_LOC):
                    used.append(hpath.split('/')[-1])
        except:
            JBoxEBSVol.log_error("error finding disk ids used in " + cid)
            return []
        return used

    @staticmethod
    def refresh_user_home_image():
        pass

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        JBoxEBSVol.LOCK.acquire()
        try:
            nfree = 0
            for idx in range(0, JBoxEBSVol.MAX_DISKS):
                dev = JBoxEBSVol.DEVICES[idx]
                if JBoxEBSVol._is_reserved(dev):
                    JBoxEBSVol.DISK_USE_STATUS[dev] = True
                else:
                    JBoxEBSVol.DISK_USE_STATUS[dev] = False
                    nfree += 1

            if container_id_list is None:
                container_id_list = [cdesc['Id'] for cdesc in JBoxContainer.session_containers(allcontainers=True)]

            for cid in container_id_list:
                disk_ids = JBoxEBSVol._get_disk_ids_used(cid)
                for disk_id in disk_ids:
                    JBoxEBSVol._mark_disk_used(disk_id)
                    nfree -= 1
            JBoxEBSVol.log_info("Disk free: " + str(nfree) + "/" + str(JBoxEBSVol.MAX_DISKS))
        finally:
            JBoxEBSVol.LOCK.release()

    @staticmethod
    def _get_unused_disk_id():
        for idx in range(0, JBoxEBSVol.MAX_DISKS):
            dev = JBoxEBSVol.DEVICES[idx]
            if not JBoxEBSVol.DISK_USE_STATUS[dev]:
                return dev
        return None

    @staticmethod
    def _is_reserved(idx):
        if (idx in JBoxEBSVol.DISK_RESERVE_TIME) and (JBoxEBSVol.DISK_RESERVE_TIME[idx] < time.time()):
            del JBoxEBSVol.DISK_RESERVE_TIME[idx]
        return idx in JBoxEBSVol.DISK_RESERVE_TIME

    @staticmethod
    def _mark_disk_used(idx, used=True, for_secs=0):
        JBoxEBSVol.DISK_USE_STATUS[idx] = used
        if used and (for_secs > 0):
            JBoxEBSVol.DISK_RESERVE_TIME[idx] = time.time() + for_secs
        else:
            if idx in JBoxEBSVol.DISK_RESERVE_TIME:
                del JBoxEBSVol.DISK_RESERVE_TIME[idx]

    @staticmethod
    def _reserve_disk_id():
        JBoxEBSVol.LOCK.acquire()
        try:
            disk_id = JBoxEBSVol._get_unused_disk_id()
            JBoxEBSVol._mark_disk_used(disk_id, for_secs=120)
            return disk_id
        finally:
            JBoxEBSVol.LOCK.release()

    @staticmethod
    def disk_ids_used_pct():
        pct = (sum(JBoxEBSVol.DISK_USE_STATUS.values()) * 100) / len(JBoxEBSVol.DISK_USE_STATUS)
        return min(100, max(0, pct))

    @staticmethod
    def get_disk_for_user(user_email):
        JBoxEBSVol.log_debug("creating EBS volume for %s", user_email)

        disk_id = JBoxEBSVol._reserve_disk_id()
        if disk_id is None:
            raise Exception("No free disk available")

        try:
            existing_disk = JBoxDiskState(cluster_id=CloudHost.INSTALL_ID, region_id=CloudHost.REGION,
                                          user_id=user_email)
        except Exception, ex:
            JBoxEBSVol.log_debug("No existing disk for %s. Exception %r", user_email, ex)
            existing_disk = None

        if existing_disk is None:
            sess_id = unique_sessname(user_email)
            sess_props = JBoxSessionProps(sess_id, create=True, user_id=user_email)
            if sess_props.is_new:
                sess_props.save()
            snap_id = sess_props.get_snapshot_id()
            if snap_id is None:
                snap_id = JBoxEBSVol.DISK_TEMPLATE_SNAPSHOT

            JBoxEBSVol.log_debug("will use snapshot id %s for %s", snap_id, user_email)

            _dev_path, mnt_path, vol_id = CloudHost.create_new_volume(snap_id, disk_id,
                                                                      JBoxEBSVol.FS_LOC,
                                                                      tag=user_email,
                                                                      disk_sz_gb=JBoxEBSVol.DISK_LIMIT)
            existing_disk = JBoxDiskState(cluster_id=CloudHost.INSTALL_ID, region_id=CloudHost.REGION,
                                          user_id=user_email,
                                          volume_id=vol_id,
                                          attach_time=None,
                                          create=True)
        else:
            _dev_path, mnt_path = CloudHost.attach_volume(existing_disk.get_volume_id(), disk_id, JBoxEBSVol.FS_LOC)
            existing_disk.set_attach_time()
            snap_id = None

        existing_disk.set_state(JBoxDiskState.STATE_ATTACHED)
        existing_disk.save()

        ebsvol = JBoxEBSVol(mnt_path, user_email=user_email)

        if snap_id == JBoxEBSVol.DISK_TEMPLATE_SNAPSHOT:
            JBoxEBSVol.log_debug("creating home folder on blank volume for %s", user_email)
            ebsvol.restore_user_home(True)
            ebsvol.restore()
        else:
            JBoxEBSVol.log_debug("updating home folder on existing volume for %s", user_email)
            ebsvol.restore_user_home(False)
        #    snap_age_days = CloudHost.get_snapshot_age(snap_id).total_seconds()/(60*60*24)
        #    if snap_age_days > 7:
        #        ebsvol.restore_user_home()
        JBoxEBSVol.log_debug("setting up instance configuration on disk for %s", user_email)
        ebsvol.setup_instance_config()

        return ebsvol

    @staticmethod
    def is_mount_path(fs_path):
        return fs_path.startswith(JBoxEBSVol.FS_LOC)

    @staticmethod
    def get_disk_from_container(cid):
        disk_ids_used = JBoxEBSVol._get_disk_ids_used(cid)
        if len(disk_ids_used) == 0:
            return None

        disk_id_used = disk_ids_used[0]
        disk_path = os.path.join(JBoxEBSVol.FS_LOC, str(disk_id_used))
        container_name = JBoxVol.get_cname(cid)
        sessname = container_name[1:]
        return JBoxEBSVol(disk_path, sessname=sessname)

    def _backup(self, clear_volume=False):
        sess_props = JBoxSessionProps(self.sessname)
        desc = sess_props.get_user_id() + " JuliaBox Backup"
        disk_id = self.disk_path.split('/')[-1]
        snap_id = CloudHost.snapshot_volume(dev_id=disk_id, tag=self.sessname, description=desc,
                                            wait_till_complete=False)
        #old_snap_id = sess_props.get_snapshot_id()
        #sess_props.set_snapshot_id(snap_id)
        #sess_props.save()
        #if old_snap_id is not None:
        #    CloudHost.delete_snapshot(old_snap_id)
        return snap_id

    def release(self, backup=False):
        disk_id = self.disk_path.split('/')[-1]
        CloudHost.unmount_device(disk_id, JBoxEBSVol.FS_LOC)
        if backup:
            snap_id = self._backup()
        else:
            snap_id = None
        vol_id = CloudHost.get_volume_id_from_device(disk_id)
        CloudHost.detach_volume(vol_id, delete=False)

        sess_props = JBoxSessionProps(self.sessname)
        existing_disk = JBoxDiskState(cluster_id=CloudHost.INSTALL_ID, region_id=CloudHost.REGION,
                                      user_id=sess_props.get_user_id())
        if snap_id is not None:
            existing_disk.add_snapshot_id(snap_id)
        existing_disk.set_detach_time()
        existing_disk.set_state(JBoxDiskState.STATE_DETACHED)
        existing_disk.save()