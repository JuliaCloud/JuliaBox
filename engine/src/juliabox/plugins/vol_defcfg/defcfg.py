import os

from juliabox.jbox_util import ensure_delete, make_sure_path_exists, unique_sessname, JBoxCfg
from juliabox.vol import JBoxVol


class JBoxDefaultConfigVol(JBoxVol):
    provides = [JBoxVol.JBP_CONFIG]

    FS_LOC = None

    @staticmethod
    def configure():
        cfg_location = os.path.expanduser(JBoxCfg.get('cfg_location'))
        make_sure_path_exists(cfg_location)
        JBoxDefaultConfigVol.FS_LOC = cfg_location

    @staticmethod
    def _get_config_mounts_used(cid):
        used = []
        props = JBoxDefaultConfigVol.dckr().inspect_container(cid)
        try:
            for _cpath, hpath in JBoxVol.extract_mounts(props):
                if hpath.startswith(JBoxDefaultConfigVol.FS_LOC):
                    used.append(hpath.split('/')[-1])
        except:
            JBoxDefaultConfigVol.log_error("error finding config mount points used in " + cid)
            return []
        return used

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        pass

    @staticmethod
    def get_disk_for_user(user_email):
        JBoxDefaultConfigVol.log_debug("creating configs disk for %s", user_email)
        if JBoxDefaultConfigVol.FS_LOC is None:
            JBoxDefaultConfigVol.configure()

        disk_path = os.path.join(JBoxDefaultConfigVol.FS_LOC, unique_sessname(user_email))
        cfgvol = JBoxDefaultConfigVol(disk_path, user_email=user_email)
        cfgvol._unpack_config()
        return cfgvol

    @staticmethod
    def is_mount_path(fs_path):
        return fs_path.startswith(JBoxDefaultConfigVol.FS_LOC)

    @staticmethod
    def get_disk_from_container(cid):
        mounts_used = JBoxDefaultConfigVol._get_config_mounts_used(cid)
        if len(mounts_used) == 0:
            return None

        mount_used = mounts_used[0]
        disk_path = os.path.join(JBoxDefaultConfigVol.FS_LOC, str(mount_used))
        container_name = JBoxVol.get_cname(cid)
        sessname = container_name[1:]
        return JBoxDefaultConfigVol(disk_path, sessname=sessname)

    @staticmethod
    def refresh_user_home_image():
        pass

    def release(self, backup=False):
        ensure_delete(self.disk_path, include_itself=True)

    @staticmethod
    def disk_ids_used_pct():
        return 0

    def _unpack_config(self):
        if os.path.exists(self.disk_path):
            JBoxDefaultConfigVol.log_debug("Config folder exists %s. Deleting...", self.disk_path)
            ensure_delete(self.disk_path, include_itself=True)
            JBoxDefaultConfigVol.log_debug("Config folder deleted %s", self.disk_path)

        JBoxDefaultConfigVol.log_debug("Will unpack config to %s", self.disk_path)
        os.mkdir(self.disk_path)
        JBoxDefaultConfigVol.log_debug("Created config folder %s", self.disk_path)

        self.restore_user_home(True)
        JBoxDefaultConfigVol.log_debug("Restored config files to %s", self.disk_path)
        self.setup_instance_config()
        JBoxDefaultConfigVol.log_debug("Setup instance config at %s", self.disk_path)