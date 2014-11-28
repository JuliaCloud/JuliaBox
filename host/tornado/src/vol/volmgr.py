import os

from jbox_util import make_sure_path_exists, LoggerMixin
from db import JBoxUserV2, JBoxDynConfig
from jbox_volume import JBoxVol
from loopback import JBoxLoopbackVol
from ebs import JBoxEBSVol
from cloud.aws import CloudHost


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
    def has_update_for_user_home_image():
        img_dir, curr_img = os.path.split(JBoxVol.USER_HOME_IMG)
        VolMgr.log_debug("checking for updates to user home image %s/%s", img_dir, curr_img)
        bucket, new_img = JBoxDynConfig.get_user_home_image(CloudHost.INSTALL_ID)
        if bucket is None:
            VolMgr.log_debug("no images configured")
            return False
        VolMgr.log_debug("latest user home image %s/%s", bucket, new_img)
        if new_img == curr_img:
            VolMgr.log_debug("already on latest image")
            return False
        return True

    @staticmethod
    def update_user_home_image(fetch=True):
        img_dir, curr_img = os.path.split(JBoxVol.USER_HOME_IMG)
        bucket, new_img = JBoxDynConfig.get_user_home_image(CloudHost.INSTALL_ID)
        new_img_path = os.path.join(img_dir, new_img)

        if fetch and (not os.path.exists(new_img_path)):
            VolMgr.log_debug("fetching new image to %s", new_img_path)
            k = CloudHost.pull_file_from_s3(bucket, new_img_path)
            if k is not None:
                VolMgr.log_debug("fetched new user home image")

        if os.path.exists(new_img_path):
            VolMgr.log_debug("set new image to %s", new_img_path)
            JBoxVol.USER_HOME_IMG = new_img_path
            return True
        return False

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
        VolMgr.log_debug("restoring disk for %s", email)
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
