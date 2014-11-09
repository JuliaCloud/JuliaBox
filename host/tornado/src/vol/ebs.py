
import os
import threading

from db import JBoxSessionProps
from jbox_util import CloudHelper, unique_sessname
from jbox_volume import JBoxVol


class JBoxEBSVol(JBoxVol):
    DEVICES = []
    MAX_DISKS = 0
    FS_LOC = None
    DISK_LIMIT = None
    DISK_USE_STATUS = {}
    DISK_TEMPLATE_SNAPSHOT = None
    HAS_EBS = False
    LOCK = None

    @staticmethod
    def configure(disk_limit, fs_loc, max_disks, disk_template_snap_id):
        JBoxEBSVol.HAS_EBS = True
        JBoxEBSVol.FS_LOC = fs_loc
        JBoxEBSVol.DISK_LIMIT = disk_limit
        JBoxEBSVol.MAX_DISKS = max_disks
        JBoxEBSVol.DEVICES = JBoxEBSVol._get_configured_devices(JBoxEBSVol.FS_LOC)
        JBoxEBSVol.DISK_TEMPLATE_SNAPSHOT = disk_template_snap_id
        if len(JBoxEBSVol.DEVICES) < max_disks:
            raise Exception("Not enough EBS mount points configured")
        JBoxEBSVol.LOCK = threading.Lock()
        JBoxEBSVol.refresh_disk_use_status()

    @classmethod
    def get_disk_allocated_size(cls):
        return JBoxEBSVol.DISK_LIMIT

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
    def refresh_disk_use_status(container_id_list=None):
        JBoxEBSVol.LOCK.acquire()
        try:
            for idx in range(0, JBoxEBSVol.MAX_DISKS):
                dev = JBoxEBSVol.DEVICES[idx]
                JBoxEBSVol.DISK_USE_STATUS[dev] = False

            nfree = JBoxEBSVol.MAX_DISKS
            if container_id_list is None:
                container_id_list = [cdesc['Id'] for cdesc in JBoxEBSVol.dckr().containers(all=True)]

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
    def _mark_disk_used(idx, used=True):
        JBoxEBSVol.DISK_USE_STATUS[idx] = used

    @staticmethod
    def _reserve_disk_id():
        JBoxEBSVol.LOCK.acquire()
        try:
            disk_id = JBoxEBSVol._get_unused_disk_id()
            JBoxEBSVol._mark_disk_used(disk_id)
            return disk_id
        finally:
            JBoxEBSVol.LOCK.release()

    @staticmethod
    def disk_ids_used_pct():
        if not JBoxEBSVol.HAS_EBS:
            return 0
        pct = (sum(JBoxEBSVol.DISK_USE_STATUS.values()) * 100) / len(JBoxEBSVol.DISK_USE_STATUS)
        return min(100, max(0, pct))

    @classmethod
    def get_disk_allocated_size(cls):
        return JBoxEBSVol.DISK_LIMIT

    @staticmethod
    def get_disk_for_user(user_email):
        if not JBoxEBSVol.HAS_EBS:
            raise Exception("EBS disks not enabled")

        disk_id = JBoxEBSVol._reserve_disk_id()
        if disk_id is None:
            raise Exception("No free disk available")

        sess_id = unique_sessname(user_email)
        sess_props = JBoxSessionProps(sess_id, create=True, user_id=user_email)
        sess_props.save()
        snap_id = sess_props.get_snapshot_id()
        if snap_id is None:
            snap_id = JBoxEBSVol.DISK_TEMPLATE_SNAPSHOT

        _dev_path, mnt_path = CloudHelper.create_new_volume(snap_id, disk_id, JBoxEBSVol.FS_LOC, tag=user_email)
        ebsvol = JBoxEBSVol(mnt_path, user_email=user_email)

        if snap_id == JBoxEBSVol.DISK_TEMPLATE_SNAPSHOT:
            ebsvol.restore_user_home()
            ebsvol.restore()
        else:
            snap_age_days = CloudHelper.get_snapshot_age(snap_id).total_seconds()/(60*60*24)
            if snap_age_days > 7:
                ebsvol.restore_user_home()
        ebsvol.setup_instance_config()

        return ebsvol

    @staticmethod
    def get_disk_from_container(cid):
        if not JBoxEBSVol.HAS_EBS:
            raise Exception("EBS disks not enabled")
        disk_ids_used = JBoxEBSVol._get_disk_ids_used(cid)
        disk_id_used = disk_ids_used[0]
        disk_path = os.path.join(JBoxEBSVol.FS_LOC, str(disk_id_used))
        container_name = JBoxVol.get_cname(cid)
        sessname = container_name[1:]
        return JBoxEBSVol(disk_path, sessname=sessname)

    def backup(self, clear_volume=False, s3backup=False):
        if not JBoxEBSVol.HAS_EBS:
            raise Exception("EBS disks not enabled")

        if s3backup:
            super(JBoxEBSVol, self).backup(clear_volume=clear_volume)
        else:
            disk_id = self.disk_path.split('/')[-1]
            sess_props = JBoxSessionProps(self.sessname)
            desc = sess_props.get_user_id() + " JuliaBox Backup"
            snap_id = CloudHelper.snapshot_volume(dev_id=disk_id, tag=self.sessname, description=desc)
            old_snap_id = sess_props.get_snapshot_id()
            sess_props.set_snapshot_id(snap_id)
            sess_props.save()
            if old_snap_id is not None:
                CloudHelper.delete_snapshot(old_snap_id)

    def release(self):
        if not JBoxEBSVol.HAS_EBS:
            raise Exception("EBS disks not enabled")
        disk_id = self.disk_path.split('/')[-1]
        CloudHelper.detach_mounted_volume(disk_id, JBoxEBSVol.FS_LOC, delete=True)