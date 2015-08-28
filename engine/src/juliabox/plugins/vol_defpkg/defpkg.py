import os
import sh
import threading
import tarfile

from juliabox.jbox_util import ensure_delete, make_sure_path_exists, JBoxCfg
from juliabox.vol import JBoxVol
from juliabox.interactive import SessContainer


class JBoxDefaultPackagesVol(JBoxVol):
    provides = [JBoxVol.JBP_PKGBUNDLE]

    FS_LOC = None
    LOCK = None
    CURRENT_BUNDLE = None
    BUNDLES_IN_USE = set()

    @staticmethod
    def configure():
        pkg_location = os.path.expanduser(JBoxCfg.get('pkg_location'))
        make_sure_path_exists(pkg_location)

        JBoxDefaultPackagesVol.FS_LOC = pkg_location
        JBoxDefaultPackagesVol.LOCK = threading.Lock()
        JBoxDefaultPackagesVol.refresh_disk_use_status()

    @staticmethod
    def _get_package_mounts_used(cid):
        used = []
        props = JBoxDefaultPackagesVol.dckr().inspect_container(cid)
        try:
            vols = props['Volumes']
            for _cpath, hpath in vols.iteritems():
                if hpath.startswith(JBoxDefaultPackagesVol.FS_LOC):
                    used.append(hpath.split('/')[-1])
        except:
            JBoxDefaultPackagesVol.log_error("error finding package mount points used in " + cid)
            return []
        return used

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        JBoxDefaultPackagesVol.LOCK.acquire()
        bundles = set()
        try:
            if container_id_list is None:
                container_id_list = [cdesc['Id'] for cdesc in SessContainer.session_containers(allcontainers=True)]

            for cid in container_id_list:
                mount_points = JBoxDefaultPackagesVol._get_package_mounts_used(cid)
                bundles.update(mount_points)

            JBoxDefaultPackagesVol.BUNDLES_IN_USE = bundles
            JBoxDefaultPackagesVol.log_info("Packages in use: %r", bundles)
        finally:
            JBoxDefaultPackagesVol.LOCK.release()

    @staticmethod
    def get_disk_for_user(user_email):
        JBoxDefaultPackagesVol.log_debug("creating default packages mounted disk for %s", user_email)
        disk_path = os.path.join(JBoxDefaultPackagesVol.FS_LOC, JBoxDefaultPackagesVol.CURRENT_BUNDLE)
        pkgvol = JBoxDefaultPackagesVol(disk_path, user_email=user_email)
        return pkgvol

    @staticmethod
    def is_mount_path(fs_path):
        return fs_path.startswith(JBoxDefaultPackagesVol.FS_LOC)

    @staticmethod
    def get_disk_from_container(cid):
        mounts_used = JBoxDefaultPackagesVol._get_package_mounts_used(cid)
        if len(mounts_used) == 0:
            return None

        mount_used = mounts_used[0]
        disk_path = os.path.join(JBoxDefaultPackagesVol.FS_LOC, str(mount_used))
        container_name = JBoxVol.get_cname(cid)
        sessname = container_name[1:]
        return JBoxDefaultPackagesVol(disk_path, sessname=sessname)

    @staticmethod
    def refresh_user_home_image():
        if not JBoxDefaultPackagesVol._has_unpacked_julia_packages():
            JBoxDefaultPackagesVol._unpack_julia_packages()
            JBoxDefaultPackagesVol._del_unused_package_extracts()

    def release(self, backup=False):
        pass

    @staticmethod
    def disk_ids_used_pct():
        return 0

    @staticmethod
    def _has_unpacked_julia_packages():
        pkg_name = os.path.basename(JBoxVol.PKG_IMG).split('.')[0]
        pkgdir = os.path.join(JBoxDefaultPackagesVol.FS_LOC, pkg_name)
        if os.path.exists(pkgdir):
            JBoxDefaultPackagesVol.log_info("Packages folder %s exists. Reusing...", pkgdir)
            # set PKG_CURRENT to the existing folder
            JBoxDefaultPackagesVol.CURRENT_BUNDLE = pkg_name
            return True
        JBoxDefaultPackagesVol.log_info("Packages folder %s does not exist.", pkgdir)
        return False

    @staticmethod
    def _unpack_julia_packages():
        pkg_name = os.path.basename(JBoxVol.PKG_IMG).split('.')[0]
        pkgdir = os.path.join(JBoxDefaultPackagesVol.FS_LOC, pkg_name)
        if os.path.exists(pkgdir):
            JBoxDefaultPackagesVol.log_debug("Packages folder exists %s. Deleting...", pkgdir)
            ensure_delete(pkgdir, include_itself=True)
            JBoxDefaultPackagesVol.log_debug("Packages folder deleted %s", pkgdir)

        JBoxDefaultPackagesVol.log_debug("Will unpack packages to %s", pkgdir)
        os.mkdir(pkgdir)
        JBoxDefaultPackagesVol.log_debug("Created packages folder")

        # unpack the latest image from PKG_IMG
        result = sh.tar("-xzf", JBoxVol.PKG_IMG, "-C", pkgdir)
        if result.exit_code != 0:
            JBoxDefaultPackagesVol.log_error("Error extracting tar file %r", result.exit_code)
            raise Exception("Error extracting packages")
        # with tarfile.open(JBoxVol.PKG_IMG, 'r:gz') as pkgs:
        #     pkgs.extractall(pkgdir)

        JBoxDefaultPackagesVol.CURRENT_BUNDLE = pkg_name
        JBoxDefaultPackagesVol.log_info("Current packages folder set to %s", pkgdir)

    @staticmethod
    def _del_unused_package_extracts(usedpkgs=None):
        if usedpkgs is None:
            usedpkgs = JBoxDefaultPackagesVol.BUNDLES_IN_USE

        # usedpkgs is the list of volumes mounted by all containers
        currdirname = os.path.basename(JBoxDefaultPackagesVol.CURRENT_BUNDLE)
        for pkgdir in os.listdir(JBoxDefaultPackagesVol.FS_LOC):
            dirname = os.path.basename(pkgdir)
            if dirname not in usedpkgs and dirname != currdirname:
                # no container uses it, delete
                JBoxDefaultPackagesVol.log_info("Deleting unused packages folder %s", dirname)
                ensure_delete(os.path.join(JBoxDefaultPackagesVol.FS_LOC, dirname), include_itself=True)
