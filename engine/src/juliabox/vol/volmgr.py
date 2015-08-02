import os
import datetime
import errno
import pytz

from juliabox.jbox_util import LoggerMixin, unique_sessname
from juliabox.db import JBoxUserV2, JBoxDynConfig
from jbox_volume import JBoxVol
from juliabox.cloud import JBoxCloudPlugin, Compute


class VolMgr(LoggerMixin):
    STATS = None
    STAT_NAME = "stat_volmgr"

    @staticmethod
    def configure():
        JBoxVol.configure()

    @staticmethod
    def has_update_for_user_home_image():
        home_img_dir, curr_home_img = os.path.split(JBoxVol.USER_HOME_IMG)
        pkg_img_dir, curr_pkg_img = os.path.split(JBoxVol.PKG_IMG)

        # VolMgr.log_debug("checking for updates to user home image %s/%s", img_dir, curr_img)
        bucket, new_pkg_img, new_home_img = JBoxDynConfig.get_user_home_image(Compute.get_install_id())

        if bucket is None:
            VolMgr.log_info("Home: none configured. current: %s/%s", home_img_dir, curr_home_img)
            return False

        if new_home_img == curr_home_img and new_pkg_img == curr_pkg_img:
            VolMgr.log_info("Home: no updates. current: %s/%s", home_img_dir, curr_home_img)
            VolMgr.log_info("Packages: no updates. current: %s/%s", pkg_img_dir, curr_pkg_img)
            return False
        else:
            VolMgr.log_info("Home: update: %s/%s. current: %s/%s", bucket, new_home_img, home_img_dir, curr_home_img)
            VolMgr.log_info("Packages: update: %s/%s. current: %s/%s", bucket, new_pkg_img, home_img_dir, curr_home_img)

        return True

    @staticmethod
    def update_user_home_image(fetch=True):
        plugin = JBoxCloudPlugin.jbox_get_plugin(JBoxCloudPlugin.PLUGIN_BUCKETSTORE)
        if plugin is None:
            VolMgr.log_info("No plugin provided for bucketstore. Can not update packages and user home images")
            return

        home_img_dir, curr_home_img = os.path.split(JBoxVol.USER_HOME_IMG)
        pkg_img_dir, curr_pkg_img = os.path.split(JBoxVol.PKG_IMG)

        bucket, new_pkg_img, new_home_img = JBoxDynConfig.get_user_home_image(Compute.get_install_id())

        new_home_img_path = os.path.join(home_img_dir, new_home_img)
        new_pkg_img_path = os.path.join(pkg_img_dir, new_pkg_img)
        updated = False
        for img_path in (new_home_img_path, new_pkg_img_path):
            if not os.path.exists(img_path):
                if fetch:
                    VolMgr.log_debug("fetching new image to %s", img_path)
                    k = plugin.pull(bucket, img_path)
                    if k is not None:
                        VolMgr.log_debug("fetched new image")

        if os.path.exists(new_home_img_path):
            VolMgr.log_debug("set new home image to %s", new_home_img_path)
            JBoxVol.USER_HOME_IMG = new_home_img_path
            updated = True

        if os.path.exists(new_pkg_img_path):
            VolMgr.log_debug("set new pkg image to %s", new_pkg_img_path)
            JBoxVol.PKG_IMG = new_pkg_img_path
            updated = True

        return updated

    @staticmethod
    def refresh_user_home_image():
        for plugin in JBoxVol.jbox_get_plugins(JBoxVol.PLUGIN_USERHOME):
            plugin.refresh_user_home_image()
        for plugin in JBoxVol.jbox_get_plugins(JBoxVol.PLUGIN_PKGBUNDLE):
            plugin.refresh_user_home_image()

    @staticmethod
    def get_disk_from_container(cid, disktype=None):
        try:
            plugins = JBoxVol.plugins if disktype is None else JBoxVol.jbox_get_plugins(disktype)
            for plugin in plugins:
                disk = plugin.get_disk_from_container(cid)
                if disk is not None:
                    return disk
        except:
            VolMgr.log_error("error finding disk ids used in " + cid)

        return None

    @staticmethod
    def get_pkg_mount_from_container(cid):
        try:
            for plugin in JBoxVol.jbox_get_plugins(JBoxVol.PLUGIN_PKGBUNDLE):
                disk = plugin.get_disk_from_container(cid)
                if disk is not None:
                    return disk
        except:
            VolMgr.log_error("error finding pkg mount used in " + cid)

        return None

    @staticmethod
    def is_mount_path(fs_path):
        for plugin in JBoxVol.plugins:
            if plugin.is_mount_path(fs_path):
                return True
        return False

    @staticmethod
    def used_pct():
        pct_home = 0.0
        for plugin in JBoxVol.jbox_get_plugins(JBoxVol.PLUGIN_USERHOME):
            pct_home += plugin.disk_ids_used_pct()
        pct_data = 0.0
        for plugin in JBoxVol.jbox_get_plugins(JBoxVol.PLUGIN_DATA):
            pct_data += plugin.disk_ids_used_pct()

        return min(100, max(pct_data, pct_home))

    @staticmethod
    def get_pkg_mount_for_user(email):
        plugin = JBoxVol.jbox_get_plugin(JBoxVol.PLUGIN_PKGBUNDLE)
        if plugin is None:
            raise Exception("No plugin found for %s" % (JBoxVol.PLUGIN_PKGBUNDLE,))
        disk = plugin.get_disk_for_user(email)
        return disk

    @staticmethod
    def get_disk_for_user(email):
        VolMgr.log_debug("restoring disk for %s", email)
        user = JBoxUserV2(email)

        custom_jimg = None
        ipython_profile = 'julia'
        # TODO: image path should be picked up from config
        if user.has_resource_profile(JBoxUserV2.RES_PROF_JULIA_PKG_PRECOMP):
            custom_jimg = '/opt/julia_packages/jimg/stable/sys.ji'
            ipython_profile = 'jboxjulia'

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

        plugin = JBoxCloudPlugin.jbox_get_plugin(JBoxCloudPlugin.PLUGIN_BUCKETSTORE)
        if plugin is not None:
            k = plugin.pull(JBoxVol.BACKUP_BUCKET, sessname + ".tar.gz", metadata_only=True)
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
        VolMgr.STATS['loopback']['min_size'] = min(sizes) if len(sizes) > 0 else 0
        VolMgr.STATS['loopback']['max_size'] = max(sizes) if len(sizes) > 0 else 0
        VolMgr.STATS['loopback']['avg_size'] = sum(sizes) / len(sizes) if len(sizes) > 0 else 0

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
        JBoxDynConfig.set_stat(Compute.get_install_id(), VolMgr.STAT_NAME, VolMgr.STATS)
