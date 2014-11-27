import os
import threading

from jbox_util import ensure_delete
from jbox_volume import JBoxVol


class JBoxLoopbackVol(JBoxVol):
    FS_LOC = None
    DISK_LIMIT = None
    MAX_CONTAINERS = 0
    MAX_DISKS = 0
    VALID_CONTAINERS = {}
    DISK_USE_STATUS = {}
    LOCK = None

    @staticmethod
    def configure(disk_limit, fs_loc, max_disks):
        JBoxLoopbackVol.DISK_LIMIT = disk_limit
        JBoxLoopbackVol.FS_LOC = fs_loc
        JBoxLoopbackVol.MAX_DISKS = max_disks
        JBoxLoopbackVol.LOCK = threading.Lock()
        JBoxLoopbackVol.refresh_disk_use_status()

    @classmethod
    def get_disk_allocated_size(cls):
        return JBoxLoopbackVol.DISK_LIMIT

    @staticmethod
    def _get_disk_ids_used(cid):
        used = []
        props = JBoxLoopbackVol.dckr().inspect_container(cid)
        try:
            vols = props['Volumes']
            for _cpath, hpath in vols.iteritems():
                if hpath.startswith(JBoxLoopbackVol.FS_LOC):
                    used.append(int(hpath.split('/')[-1]))
        except:
            JBoxLoopbackVol.log_error("error finding disk ids used in " + cid)
            return []
        return used

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        JBoxLoopbackVol.LOCK.acquire()
        try:
            for idx in range(0, JBoxLoopbackVol.MAX_DISKS):
                JBoxLoopbackVol.DISK_USE_STATUS[idx] = False

            nfree = JBoxLoopbackVol.MAX_DISKS
            if container_id_list is None:
                container_id_list = [cdesc['Id'] for cdesc in JBoxLoopbackVol.dckr().containers(all=True)]

            for cid in container_id_list:
                disk_ids = JBoxLoopbackVol._get_disk_ids_used(cid)
                for disk_id in disk_ids:
                    JBoxLoopbackVol._mark_disk_used(disk_id)
                    nfree -= 1
            JBoxLoopbackVol.log_info("Disk free: " + str(nfree) + "/" + str(JBoxLoopbackVol.MAX_DISKS))
        finally:
            JBoxLoopbackVol.LOCK.release()

    @staticmethod
    def disk_ids_used_pct():
        pct = (sum(JBoxLoopbackVol.DISK_USE_STATUS.values()) * 100) / len(JBoxLoopbackVol.DISK_USE_STATUS)
        return min(100, max(0, pct))

    @staticmethod
    def _get_unused_disk_id():
        for idx in range(0, JBoxLoopbackVol.MAX_DISKS):
            if not JBoxLoopbackVol.DISK_USE_STATUS[idx]:
                return idx
        return -1

    @staticmethod
    def _mark_disk_used(idx, used=True):
        JBoxLoopbackVol.DISK_USE_STATUS[idx] = used

    @staticmethod
    def _reserve_disk_id():
        JBoxLoopbackVol.LOCK.acquire()
        try:
            disk_id = JBoxLoopbackVol._get_unused_disk_id()
            JBoxLoopbackVol._mark_disk_used(disk_id)
            return disk_id
        finally:
            JBoxLoopbackVol.LOCK.release()

    @staticmethod
    def get_disk_for_user(user_email):
        JBoxLoopbackVol.log_debug("creating loopback mounted disk for %s", user_email)
        disk_id = JBoxLoopbackVol._reserve_disk_id()
        if disk_id < 0:
            raise Exception("No free disk available")
        disk_path = os.path.join(JBoxLoopbackVol.FS_LOC, str(disk_id))
        JBoxLoopbackVol.log_debug("blanking out disk for %s", user_email)
        ensure_delete(disk_path)
        loopvol = JBoxLoopbackVol(disk_path, user_email=user_email)

        JBoxLoopbackVol.log_debug("restoring data for %s", user_email)
        loopvol.restore_user_home()
        loopvol.setup_instance_config()
        loopvol.restore()
        return loopvol

    @staticmethod
    def get_disk_from_container(cid):
        disk_ids_used = JBoxLoopbackVol._get_disk_ids_used(cid)
        disk_id_used = disk_ids_used[0]
        disk_path = os.path.join(JBoxLoopbackVol.FS_LOC, str(disk_id_used))
        container_name = JBoxVol.get_cname(cid)
        sessname = container_name[1:]
        return JBoxLoopbackVol(disk_path, sessname=sessname)

    def _backup(self, clear_volume=True):
        super(JBoxLoopbackVol, self)._backup(clear_volume=clear_volume)

    def release(self, backup=False):
        if backup:
            self._backup()