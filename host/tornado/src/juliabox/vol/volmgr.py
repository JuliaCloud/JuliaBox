import os
import datetime
import errno
import pytz

from juliabox.jbox_util import LoggerMixin, JBoxCfg, unique_sessname
from juliabox.db import JBoxUserV2, JBoxDynConfig
from jbox_volume import JBoxVol
from juliabox.cloud.aws import CloudHost


class VolMgr(LoggerMixin):
    STATS = None
    STAT_NAME = "stat_volmgr"

    @staticmethod
    def configure():
        JBoxVol.configure()

    @staticmethod
    def has_update_for_user_home_image():
        img_dir, curr_img = os.path.split(JBoxVol.USER_HOME_IMG)
        #VolMgr.log_debug("checking for updates to user home image %s/%s", img_dir, curr_img)
        bucket, new_img = JBoxDynConfig.get_user_home_image(CloudHost.INSTALL_ID)
        if bucket is None:
            VolMgr.log_info("User home image: none configured. current: %s/%s", img_dir, curr_img)
            return False
        if new_img == curr_img:
            VolMgr.log_info("User home image: no updates. current: %s/%s", img_dir, curr_img)
            return False
        else:
            VolMgr.log_info("User home image: update: %s/%s. current: %s/%s", bucket, new_img, img_dir, curr_img)
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
    def refresh_user_home_image():
        for plugin in JBoxVol.plugins:
            plugin.refresh_user_home_image()

    @staticmethod
    def get_disk_from_container(cid):
        try:
            for plugin in JBoxVol.plugins:
                disk = plugin.get_disk_from_container(cid)
                if disk is not None:
                    return disk
        except:
            VolMgr.log_error("error finding disk ids used in " + cid)

        return None

    @staticmethod
    def is_mount_path(fs_path):
        for plugin in JBoxVol.plugins:
            if plugin.is_mount_path(fs_path):
                return True
        return False

    @staticmethod
    def used_pct():
        pct = 0.0
        for plugin in JBoxVol.plugins:
            pct += plugin.disk_ids_used_pct()

        return min(100, max(0, pct))

    @staticmethod
    def get_disk_for_user(email):
        VolMgr.log_debug("restoring disk for %s", email)
        user = JBoxUserV2(email)

        custom_jimg = None
        ipython_profile = 'julia'
        # TODO: image path should be picked up from config
        if user.has_resource_profile(JBoxUserV2.RES_PROF_JULIA_PKG_PRECOMP):
            custom_jimg = '/home/juser/.juliabox/jimg/sys.ji'
            ipython_profile = 'jboxjulia'

        plugin = None
        if user.has_resource_profile(JBoxUserV2.RES_PROF_DISK_EBS_1G):
            plugin = JBoxVol.jbox_get_plugin(JBoxVol.PLUGIN_EBS_USERHOME)

        # if no EBS plugin configured, use the base plugin
        if plugin is None:
            plugin = JBoxVol.jbox_get_plugin(JBoxVol.PLUGIN_USERHOME)

        if plugin is None:
            raise Exception("No plugin found for %s" % (JBoxVol.PLUGIN_USERHOME,))

        disk = plugin.get_disk_for_user(email)

        try:
            disk.setup_julia_image(ipython_profile, custom_jimg)
            disk.setup_tutorial_link()
            disk.gen_ssh_key()
            disk.gen_gitconfig()
        except IOError, ioe:
            if ioe.errno == errno.ENOSPC:
                # continue login on ENOSPC to allow user to delete files
                JBoxVol.log_exception("No space left to configure JuliaBox for %s", email)
            else:
                raise

        return disk

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        for plugin in JBoxVol.plugins:
            plugin.refresh_disk_use_status(container_id_list=container_id_list)

    @staticmethod
    def calc_stat(user_email):
        VolMgr.STATS['num_users'] += 1
        sessname = unique_sessname(user_email)

        k = CloudHost.pull_file_from_s3(JBoxVol.BACKUP_BUCKET, sessname + ".tar.gz", metadata_only=True)
        if k is not None:
            VolMgr.STATS['loopback']['sizes'].append(k.size)

    @staticmethod
    def calc_stats():
        VolMgr.STATS = {
            'date': '',
            'num_users': 0,
            'loopback': {
                'num_files': 0,
                'total_size': 0,
                'sizes': [],
                'min_size': 0,
                'max_size': 0,
                'avg_size': 0,
                'sizes_hist': {
                    'counts': [],
                    'bins': []
                }
            }
        }

        result_set = JBoxUserV2.table().scan(attributes=('user_id',))
        for user in result_set:
            VolMgr.calc_stat(user['user_id'])

        sizes = VolMgr.STATS['loopback']['sizes']
        VolMgr.STATS['loopback']['num_files'] = len(sizes)
        VolMgr.STATS['loopback']['total_size'] = sum(sizes)
        VolMgr.STATS['loopback']['min_size'] = min(sizes)
        VolMgr.STATS['loopback']['max_size'] = max(sizes)
        VolMgr.STATS['loopback']['avg_size'] = sum(sizes) / len(sizes)

        bin_size = int((VolMgr.STATS['loopback']['max_size'] - VolMgr.STATS['loopback']['min_size']) / 10)
        min_size = VolMgr.STATS['loopback']['min_size']
        bins = []
        for idx in range(0, 10):
            bins.append(min_size + bin_size*idx)
        bins.append(VolMgr.STATS['loopback']['max_size'])
        counts = [0] * 10

        for size in sizes:
            for idx in range(1, 11):
                if size <= bins[idx]:
                    counts[idx-1] += 1
                    break
        VolMgr.STATS['loopback']['sizes_hist']['counts'] = counts
        VolMgr.STATS['loopback']['sizes_hist']['bins'] = bins
        del VolMgr.STATS['loopback']['sizes']
        VolMgr.STATS['date'] = datetime.datetime.now(pytz.utc).isoformat()

    @staticmethod
    def publish_stats():
        VolMgr.calc_stats()
        VolMgr.log_debug("stats: %r", VolMgr.STATS)
        JBoxDynConfig.set_stat(CloudHost.INSTALL_ID, VolMgr.STAT_NAME, VolMgr.STATS)