import os
import psutil

from juliabox.jbox_util import ensure_delete, JBoxCfg, unique_sessname
from juliabox.vol import JBoxVol


class JBoxHostDiskVol(JBoxVol):
    provides = [JBoxVol.JBP_USERHOME, JBoxVol.JBP_USERHOME_LOCAL]

    FS_LOC = None

    @staticmethod
    def configure():
        JBoxHostDiskVol.FS_LOC = os.path.expanduser(JBoxCfg.get('mnt_location'))
        JBoxHostDiskVol.refresh_disk_use_status()

    @classmethod
    def get_disk_allocated_size(cls):
        try:
            return psutil.disk_usage(JBoxHostDiskVol.FS_LOC).total
        except:
            return 0

    @staticmethod
    def _get_disk_ids_used(cid):
        used = []
        try:
            props = JBoxHostDiskVol.dckr().inspect_container(cid)
            for _cpath, hpath in JBoxVol.extract_mounts(props):
                if hpath.startswith(JBoxHostDiskVol.FS_LOC):
                    used.append(hpath.split('/')[-1])
        except:
            JBoxHostDiskVol.log_exception("error finding disk ids used in " + cid)
            return []
        return used

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        pass

    @staticmethod
    def disk_ids_used_pct():
        try:
            return psutil.disk_usage(JBoxHostDiskVol.FS_LOC).percent
        except:
            return 0

    @staticmethod
    def get_disk_for_user(user_email):
        JBoxHostDiskVol.log_debug("creating host disk for %s", user_email)

        disk_id = unique_sessname(user_email)
        disk_path = os.path.join(JBoxHostDiskVol.FS_LOC, disk_id)
        if not os.path.exists(disk_path):
            os.mkdir(disk_path)
        hostvol = JBoxHostDiskVol(disk_path, user_email=user_email)
        hostvol.refresh_disk(mark_refreshed=False)

        if JBoxVol.BACKUP_LOC is not None:
            JBoxHostDiskVol.log_debug("restoring data for %s", user_email)
            hostvol.restore()

        return hostvol

    @staticmethod
    def is_mount_path(fs_path):
        return fs_path.startswith(JBoxHostDiskVol.FS_LOC)

    @staticmethod
    def get_disk_from_container(cid):
        disk_ids_used = JBoxHostDiskVol._get_disk_ids_used(cid)
        if len(disk_ids_used) == 0:
            return None

        disk_id_used = disk_ids_used[0]
        disk_path = os.path.join(JBoxHostDiskVol.FS_LOC, disk_id_used)
        container_name = JBoxVol.get_cname(cid)
        sessname = container_name[1:]
        return JBoxHostDiskVol(disk_path, sessname=sessname)

    @staticmethod
    def refresh_user_home_image():
        pass

    def _backup(self, clear_volume=True):
        if JBoxVol.BACKUP_LOC is not None:
            super(JBoxHostDiskVol, self)._backup(clear_volume=clear_volume)

    def refresh_disk(self, mark_refreshed=True):
        if JBoxVol.BACKUP_LOC is None:
            self.log_debug("restoring common data on disk at %s", self.disk_path)
            self.restore_user_home(False)
        else:
            self.log_debug("blanking out disk at %s", self.disk_path)
            ensure_delete(self.disk_path)
            self.log_debug("restoring common data on disk at %s", self.disk_path)
            self.restore_user_home(True)

        self.setup_instance_config()
        if mark_refreshed:
            self.mark_refreshed()
        self.log_debug("refreshed disk at %s", self.disk_path)

    def release(self, backup=False):
        if backup:
            self._backup()
        self.refresh_disk()
