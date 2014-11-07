import os

from jbox_util import make_sure_path_exists, LoggerMixin
from db import JBoxUserV2
from jbox_volume import JBoxVol
from loopback import JBoxLoopbackVol
from ebs import JBoxEBSVol


class VolMgr(LoggerMixin):
    HAS_EBS = False

    @staticmethod
    def configure(dckr, cfg):
        cloud_cfg = cfg['cloud_host']

        backup_location = os.path.expanduser(cfg['backup_location'])
        user_home_img = os.path.expanduser(cfg['user_home_image'])
        mnt_location = os.path.expanduser(cfg['mnt_location'])
        backup_bucket = cloud_cfg['backup_bucket']
        num_disks_max = cfg["numdisksmax"]
        make_sure_path_exists(backup_location)

        JBoxVol.configure_base(dckr, user_home_img, backup_location, backup_bucket=backup_bucket)
        JBoxLoopbackVol.configure(cfg['disk_limit'], mnt_location, num_disks_max)
        if cloud_cfg['ebs']:
            VolMgr.HAS_EBS = True
            ebs_mnt_location = os.path.expanduser(cloud_cfg['ebs_mnt_location'])
            JBoxEBSVol.configure(1000000000, ebs_mnt_location, num_disks_max, cloud_cfg['ebs_template'])

    @staticmethod
    def get_disk_from_container(cid):
        props = JBoxVol.dckr().inspect_container(cid)
        vols = props['Volumes']
        for _cpath, hpath in vols.iteritems():
            if hpath.startswith(JBoxLoopbackVol.FS_LOC):
                return JBoxLoopbackVol.get_disk_from_container(cid)
            elif VolMgr.HAS_EBS and hpath.startswith(JBoxEBSVol.FS_LOC):
                return JBoxEBSVol.get_disk_from_container(cid)
        return None

    @staticmethod
    def is_mount_path(fs_path):
        return fs_path.startswith(JBoxLoopbackVol.FS_LOC) or (VolMgr.HAS_EBS and fs_path.startswith(JBoxEBSVol.FS_LOC))

    @staticmethod
    def used_pct():
        pct = JBoxLoopbackVol.disk_ids_used_pct()
        if VolMgr.HAS_EBS:
            pct += JBoxEBSVol.disk_ids_used_pct()
        return min(100, max(0, pct))

    @staticmethod
    def get_disk_for_user(email):
        ebs = False

        if VolMgr.HAS_EBS:
            user = JBoxUserV2(email)
            ebs = user.has_resource_profile(JBoxUserV2.RESOURCE_PROFILE_DISK_EBS_1G)

        if ebs:
            return JBoxEBSVol.get_disk_for_user(email)
        else:
            return JBoxLoopbackVol.get_disk_for_user(email)

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        JBoxLoopbackVol.refresh_disk_use_status(container_id_list=container_id_list)
        if VolMgr.HAS_EBS:
            JBoxEBSVol.refresh_disk_use_status(container_id_list=container_id_list)
