import os
import threading
import time

from juliabox.jbox_util import ensure_delete, JBoxCfg
from juliabox.vol import JBoxVol
from juliabox.interactive import SessContainer


class JBoxLoopbackVol(JBoxVol):
    provides = [JBoxVol.JBP_USERHOME, JBoxVol.JBP_USERHOME_LOCAL]

    FS_LOC = None
    DISK_LIMIT = None
    MAX_DISKS = 0
    DISK_USE_STATUS = {}
    DISK_RESERVE_TIME = {}
    LOCK = None

    @staticmethod
    def configure():
        JBoxLoopbackVol.DISK_LIMIT = JBoxCfg.get('disk_limit')
        JBoxLoopbackVol.FS_LOC = os.path.expanduser(JBoxCfg.get('mnt_location'))
        JBoxLoopbackVol.MAX_DISKS = JBoxCfg.get('numdisksmax')
        JBoxLoopbackVol.LOCK = threading.Lock()
        JBoxLoopbackVol.refresh_disk_use_status()

    @classmethod
    def get_disk_allocated_size(cls):
        return JBoxLoopbackVol.DISK_LIMIT

    @staticmethod
    def _get_disk_ids_used(cid):
        used = []
        try:
            props = JBoxLoopbackVol.dckr().inspect_container(cid)
            for _cpath, hpath in JBoxVol.extract_mounts(props):
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
            nfree = 0
            for idx in range(0, JBoxLoopbackVol.MAX_DISKS):
                if JBoxLoopbackVol._is_reserved(idx):
                    JBoxLoopbackVol.DISK_USE_STATUS[idx] = True
                else:
                    JBoxLoopbackVol.DISK_USE_STATUS[idx] = False
                    nfree += 1

            if container_id_list is None:
                container_id_list = [cdesc['Id'] for cdesc in SessContainer.session_containers(allcontainers=True)]

            for cid in container_id_list:
                disk_ids = JBoxLoopbackVol._get_disk_ids_used(cid)
                for disk_id in disk_ids:
                    JBoxLoopbackVol._mark_disk_used(disk_id)
                    nfree -= 1
            JBoxLoopbackVol.log_info("Loopback Disk free: " + str(nfree) + "/" + str(JBoxLoopbackVol.MAX_DISKS))
        finally:
            JBoxLoopbackVol.LOCK.release()

    @staticmethod
    def disk_ids_used_pct():
        pct = (sum(JBoxLoopbackVol.DISK_USE_STATUS.values()) * 100) / len(JBoxLoopbackVol.DISK_USE_STATUS)
        return min(100, max(0, pct))

    @staticmethod
    def _get_unused_disk_id(begin_idx=0):
        for idx in range(begin_idx, JBoxLoopbackVol.MAX_DISKS):
            if not JBoxLoopbackVol.DISK_USE_STATUS[idx]:
                return idx
        return -1

    @staticmethod
    def _is_reserved(idx):
        if (idx in JBoxLoopbackVol.DISK_RESERVE_TIME) and (JBoxLoopbackVol.DISK_RESERVE_TIME[idx] < time.time()):
            del JBoxLoopbackVol.DISK_RESERVE_TIME[idx]
        return idx in JBoxLoopbackVol.DISK_RESERVE_TIME

    @staticmethod
    def _mark_disk_used(idx, used=True, for_secs=0):
        JBoxLoopbackVol.DISK_USE_STATUS[idx] = used
        if used and (for_secs > 0):
            JBoxLoopbackVol.DISK_RESERVE_TIME[idx] = time.time() + for_secs
        else:
            if idx in JBoxLoopbackVol.DISK_RESERVE_TIME:
                del JBoxLoopbackVol.DISK_RESERVE_TIME[idx]

    @staticmethod
    def _reserve_disk_id(begin_idx=0):
        JBoxLoopbackVol.LOCK.acquire()
        try:
            disk_id = JBoxLoopbackVol._get_unused_disk_id(begin_idx=begin_idx)
            if disk_id >= 0:
                JBoxLoopbackVol._mark_disk_used(disk_id, for_secs=120)
            return disk_id
        finally:
            JBoxLoopbackVol.LOCK.release()

    @staticmethod
    def _unreserve_disk_id(idx):
        JBoxLoopbackVol.LOCK.acquire()
        try:
            JBoxLoopbackVol._mark_disk_used(idx, used=False)
        finally:
            JBoxLoopbackVol.LOCK.release()

    @staticmethod
    def get_disk_for_user(user_email):
        JBoxLoopbackVol.log_debug("creating loopback mounted disk for %s", user_email)
        disk_id = JBoxLoopbackVol._reserve_disk_id()
        if disk_id < 0:
            raise Exception("No free disk available")
        disk_path = os.path.join(JBoxLoopbackVol.FS_LOC, str(disk_id))
        loopvol = JBoxLoopbackVol(disk_path, user_email=user_email)
        loopvol.refresh_disk()
        JBoxLoopbackVol.log_debug("restoring data for %s", user_email)
        loopvol.restore()
        return loopvol

    @staticmethod
    def is_mount_path(fs_path):
        return fs_path.startswith(JBoxLoopbackVol.FS_LOC)

    @staticmethod
    def get_disk_from_container(cid):
        disk_ids_used = JBoxLoopbackVol._get_disk_ids_used(cid)
        if len(disk_ids_used) == 0:
            return None

        disk_id_used = disk_ids_used[0]
        disk_path = os.path.join(JBoxLoopbackVol.FS_LOC, str(disk_id_used))
        container_name = JBoxVol.get_cname(cid)
        sessname = container_name[1:]
        return JBoxLoopbackVol(disk_path, sessname=sessname)

    @staticmethod
    def refresh_user_home_image():
        pass

    def _backup(self, clear_volume=True):
        super(JBoxLoopbackVol, self)._backup(clear_volume=clear_volume)

    def refresh_disk(self):
        self.log_debug("blanking out disk at %s", self.disk_path)
        ensure_delete(self.disk_path)
        self.log_debug("refreshed disk at %s", self.disk_path)

    def release(self, backup=False):
        if backup:
            self._backup()
        self.refresh_disk()
