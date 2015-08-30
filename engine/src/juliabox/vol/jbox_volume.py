import os
import tarfile
import time
import stat
import datetime
import errno
import json
import pytz

from juliabox.cloud import JBPluginCloud, Compute
from juliabox.jbox_util import unique_sessname, ensure_delete, esc_sessname, get_user_name, parse_iso_time
from juliabox.jbox_util import LoggerMixin, JBoxCfg, make_sure_path_exists
from juliabox.jbox_util import JBoxPluginType
from juliabox.jbox_util import create_host_mnt_command, create_container_mnt_command
from juliabox.jbox_crypto import ssh_keygen


class JBoxVol(LoggerMixin):
    """ Provides storage volumes that are mounted on to containers. All volume providers must extend from `JBoxVol`.

    - `JBoxVol.JBP_USERHOME`, `JBoxVol.JBP_USERHOME_EBS`, `JBoxVol.JBP_USERHOME_LOCAL`:
        Provide storage for user home folder. These are usually faster but limited to smaller sizes.
        User home folders are overlaid with some configuration files required for working of JuliaBox.
    - `JBoxVol.JBP_DATA`, `JBoxVol.JBP_DATA_EBS`:
        Provide larger volumes for storing data.
    - `JBoxVol.JBP_PKGBUNDLE`:
        Provide read-only volumes that contain Julia packages and can be mounted on to containers.

    All volume providers must implement the following methods:
    - `configure()`: Initialize self. Configuration file can be accessed through JBoxCfg.
    - `get_disk_for_user(user_id)`: Create, initialize and return an object representing a disk for the gived user id.
    - `get_disk_from_container(cid)`: Return an object representing the disk mounted in the provided container if any.
    - `is_mount_path(fs_path)`: Check if the provided path belongs to a disk managed by the plugin.
    - `refresh_disk_use_status(container_id_list=None)`: Update status of all disks managed by the plugin by iterating through all containers.
    - `disk_ids_used_pct()`: Percent of configured disks in use (indicates load on the system).
    - `refresh_user_home_image()`: Update any pre-created disk images with a freshly downloaded JuliaBox user home image. Not required for data volumes.
    - `release(backup)`: Release the disk. Backup contents if indicated.
    """

    __metaclass__ = JBoxPluginType
    JBP_USERHOME = 'vol.userhome'
    JBP_DATA = 'vol.data'
    JBP_PKGBUNDLE = 'vol.pkgbundle'
    JBP_USERHOME_EBS = 'vol.userhome.ebs'
    JBP_USERHOME_LOCAL = 'vol.userhome.local'
    JBP_DATA_EBS = 'vol.data.ebs'

    BACKUP_LOC = None
    DCKR = None
    LOCAL_TZ_OFFSET = 0
    BACKUP_BUCKET = None
    NOTEBOOK_WEBSOCK_PROTO = "wss://"

    # includes configuration files/folders and scripts to be placed into user home folder
    USER_HOME_IMG = None
    # includes Julia packages and compiled images to be linked into from user home folder
    PKG_IMG = None
    PKG_MOUNT_POINT = '/opt/julia_packages'
    # mount point for data disk on the container
    DATA_MOUNT_POINT = '/mnt/data'

    # files that must be restored from user home for proper functioning of JuliaBox
    USER_HOME_ESSENTIALS = ['.juliabox', '.ipython/README', '.ipython/kernels',
                            '.ipython/profile_julia', '.ipython/profile_default']

    SH_DEVICE_VERSION = None

    def __init__(self, disk_path, user_email=None, user_name=None, sessname=None, old_sessname=None):
        self.disk_path = disk_path
        self.user_email = user_email

        if user_name is not None:
            self.user_name = user_name
        elif user_email is not None:
            self.user_name = get_user_name(user_email)
        else:
            self.user_name = None

        if sessname is not None:
            self.sessname = sessname
        elif user_email is not None:
            self.sessname = unique_sessname(user_email)
        else:
            self.sessname = None

        if old_sessname is not None:
            self.old_sessname = old_sessname
        elif user_email is not None:
            self.old_sessname = esc_sessname(user_email)
        else:
            self.old_sessname = None

        self._dbg_str = str(self.sessname) + "(" + self.disk_path + ")"

    @classmethod
    def dckr(cls):
        return JBoxVol.DCKR

    @classmethod
    def get_cname(cls, cid):
        props = JBoxVol.DCKR.inspect_container(cid)
        return props['Name'] if ('Name' in props) else None

    @classmethod
    def get_pid(cls, cid):
        props = JBoxVol.DCKR.inspect_container(cid)
        state = props['State']
        return state['Pid'] if state['Running'] else None

    # this is template method
    @staticmethod
    def configure():
        backup_location = JBoxCfg.get('backup_location')
        if backup_location is not None:
            backup_location = os.path.expanduser(backup_location)
            make_sure_path_exists(backup_location)
            JBoxVol.BACKUP_LOC = backup_location

        JBoxVol.DCKR = JBoxCfg.dckr
        JBoxVol.NOTEBOOK_WEBSOCK_PROTO = JBoxCfg.get('websocket_protocol') + '://'
        JBoxVol.USER_HOME_IMG = os.path.expanduser(JBoxCfg.get('user_home_image'))
        JBoxVol.PKG_IMG = os.path.expanduser(JBoxCfg.get('pkg_image'))
        JBoxVol.LOCAL_TZ_OFFSET = JBoxVol.local_time_offset()
        JBoxVol.BACKUP_BUCKET = JBoxCfg.get('cloud_host.backup_bucket')

        for plugin in JBoxVol.plugins:
            assert issubclass(plugin, JBoxVol)
            plugin.configure()
            JBoxVol.log_info("Found plugin %r provides %r", plugin, plugin.provides)

        if len(JBoxVol.plugins) == 0:
            JBoxVol.log_warn("No plugins found!")

        if JBoxVol.SH_DEVICE_VERSION is None:
            JBoxVol.SH_DEVICE_VERSION = create_host_mnt_command('stat --format 0x%t,0x%T')

    @staticmethod
    def duplicate_host_blockdevice(device, cpid):
        device_versions = JBoxVol.SH_DEVICE_VERSION(device)
        device_versions = [int(x, 16) for x in device_versions.split(',')]

        # mknod the same device in the container
        # can check existing device as: sh -c "[ -b /dev/loop1 ] || mknod --mode 0600 /dev/loop1 b 7 0
        # but safer not to overwrite any existing device and throw error instead
        mknod_cmd = "mknod --mode 0600 %s  b %d %d" % (device, device_versions[0], device_versions[1])
        cmknod = create_container_mnt_command(cpid, mknod_cmd)
        cmknod()
        return True

    @staticmethod
    def mount_host_device(device, cid, container_path):
        try:
            cpid = JBoxVol.get_pid(cid)
            JBoxVol.duplicate_host_blockdevice(device, cpid)
            mount_cmd = "mount %s %s" % (device, container_path)
            cmount = create_container_mnt_command(cpid, mount_cmd)
            cmount()
            return True
        except:
            JBoxVol.log_exception("Exception mounting device %s at %s/%s", device. cid, container_path)
            return False

    @staticmethod
    def unmount_host_device(device, cid):
        try:
            cpid = JBoxVol.get_pid(cid)
            cumount = create_container_mnt_command(cpid, "umount %s" % (device,))
            crmdev = create_container_mnt_command(cpid, "rm %s" % (device,))
            cumount()
            crmdev()
            return True
        except:
            JBoxVol.log_exception("Exception unmounting device %s from %s", device. cid)
            return False

    def debug_str(self):
        return self._dbg_str

    def gen_gitconfig(self):
        gitconfig_path = os.path.join(self.disk_path, '.gitconfig')
        if os.path.exists(gitconfig_path):
            return
        with open(gitconfig_path, 'w') as f:
            f.write("[user]\n    email = " + self.user_email + "\n    name = " + self.user_name + "\n")

    def gen_ssh_key(self):
        ssh_path = os.path.join(self.disk_path, '.ssh')
        ssh_key_path = os.path.join(ssh_path, 'id_rsa')
        ssh_pub_key_path = os.path.join(ssh_path, 'id_rsa.pub')

        if not os.path.exists(ssh_path):
            os.mkdir(ssh_path)
            os.chmod(ssh_path, 0700)

        if os.path.exists(ssh_key_path) and os.path.exists(ssh_pub_key_path):
            return
        if os.path.exists(ssh_key_path) and not os.access(ssh_key_path, os.W_OK):
            os.chmod(ssh_key_path, 0600)
        if os.path.exists(ssh_pub_key_path) and not os.access(ssh_pub_key_path, os.W_OK):
            os.chmod(ssh_pub_key_path, 0644)

        public_key, private_key = ssh_keygen()
        public_key += " juliabox\n"
        private_key += "\n"
        with open(ssh_key_path, 'w') as f:
            f.write(private_key)
        with open(ssh_pub_key_path, 'w') as f:
            f.write(public_key)
        os.chmod(ssh_key_path, 0600)
        os.chmod(ssh_pub_key_path, 0644)

    @staticmethod
    def _get_user_home_timestamp():
        user_home_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(JBoxVol.USER_HOME_IMG), pytz.utc) + \
            datetime.timedelta(seconds=JBoxVol.LOCAL_TZ_OFFSET)
        return user_home_mtime

    def mark_refreshed(self):
        marker = os.path.join(self.disk_path, '.juliabox/.refreshed')
        with open(marker, 'w') as mfile:
            mfile.write(self._get_user_home_timestamp().isoformat())

    def is_refreshed(self):
        marker = os.path.join(self.disk_path, '.juliabox/.refreshed')
        if not os.path.exists(marker):
            return False
        try:
            with open(marker, 'r') as mfile:
                dt = parse_iso_time(mfile.read())
            self.log_info("disk refreshed date: %r. user home timestamp: %r", dt, self._get_user_home_timestamp())
            return dt >= self._get_user_home_timestamp()
        except:
            self.log_error("Error reading refreshed marker from disk %s", self.disk_path)
            return False

    def unmark_refreshed(self):
        marker = os.path.join(self.disk_path, '.juliabox/.refreshed')
        if os.path.exists(marker):
            os.remove(marker)

    @staticmethod
    def _is_path_user_home_essential(chk_path):
        chk_path = os.path.normpath(chk_path)
        for p in JBoxVol.USER_HOME_ESSENTIALS:
            if chk_path.startswith(p) and ((len(p) == len(chk_path)) or (chk_path[len(p)] == os.path.sep)):
                return True
        return False

    def restore_user_home(self, new_disk):
        with tarfile.open(JBoxVol.USER_HOME_IMG, 'r:gz') as user_home:
            if new_disk:
                user_home.extractall(self.disk_path)
            else:
                # extract .juliabox, .ipython/README, .ipython/kernels,
                # .ipython/profile_julia, .ipython/profile_default
                for path in JBoxVol.USER_HOME_ESSENTIALS:
                    full_path = os.path.join(self.disk_path, path)
                    if os.path.exists(full_path):
                        ensure_delete(full_path, include_itself=True)

                for info in user_home.getmembers():
                    if not JBoxVol._is_path_user_home_essential(info.name):
                        continue
                    user_home.extract(info, self.disk_path)

    @staticmethod
    def replace_in_file(filepath, startstring, replacement):
        filepath_temp = filepath + '.temp'

        if os.path.exists(filepath_temp):
            os.remove(filepath_temp)
        if not os.path.exists(filepath):
            open(filepath, 'a').close()
        os.rename(filepath, filepath_temp)

        replaced = False
        with open(filepath_temp) as fin, open(filepath, 'w') as fout:
            for line in fin:
                if line.startswith(startstring):
                    replaced = True
                    if replacement is None:
                        continue
                    line = replacement
                fout.write(line)
            if (not replaced) and (replacement is not None):
                fout.write(replacement)
        os.remove(filepath_temp)

    def setup_julia_image(self, custom_jimg):
        # switch profile in kernel.json
        # this hack should not be required once we move completely to Julia 0.4
        kernel_path = os.path.join(self.disk_path, ".ipython", "kernels", "julia-0.3", "kernel.json")
        kernel_cfg = {
            "argv": ["/usr/bin/julia"],
            "display_name": "Julia 0.3.11",
            "language": "julia"
        }

        if custom_jimg is not None:
            kernel_cfg['argv'].extend(["-J", custom_jimg])
        kernel_cfg['argv'].extend(["-i", "-F", "/opt/julia_packages/.julia/v0.3/IJulia/src/kernel.jl", "{connection_file}"])
        with open(kernel_path, 'w') as kout:
            kout.write(json.dumps(kernel_cfg, indent=4))

        # add/remove alias in .bashrc
        bashrc_path = os.path.join(self.disk_path, ".bashrc")
        new_alias = None if custom_jimg is None else ("alias julia=\"julia -J " + custom_jimg + "\"\n")
        JBoxVol.replace_in_file(bashrc_path, "alias julia", new_alias)

    def setup_tutorial_link(self):
        tut_link = os.path.join(self.disk_path, "tutorial")
        tut_path = os.path.join("/home", "juser", ".juliabox", "tutorial")
        if not (os.path.exists(tut_link) or os.path.lexists(tut_link)):
            os.symlink(tut_path, tut_link)

    def setup_instance_config(self, profiles=('default',)):
        for profile in profiles:
            profile_path = '.ipython/profile_' + profile
            profile_path = os.path.join(self.disk_path, profile_path)
            if not os.path.exists(profile_path):
                continue
            nbconfig = os.path.join(profile_path, 'ipython_notebook_config.py')
            wsock_cfg = "c.NotebookApp.websocket_url = '" + JBoxVol.NOTEBOOK_WEBSOCK_PROTO + \
                        Compute.get_alias_hostname() + "'\n"
            JBoxVol.replace_in_file(nbconfig, "c.NotebookApp.websocket_url", wsock_cfg)

    @staticmethod
    def local_time_offset():
        """Return offset of local zone from GMT"""
        if time.localtime().tm_isdst and time.daylight:
            return time.altzone
        else:
            return time.timezone

    @staticmethod
    def pull_from_bucketstore(local_file, metadata_only=False):
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_BUCKETSTORE)
        if plugin is None or JBoxVol.BACKUP_BUCKET is None:
            return None
        return plugin.pull(JBoxVol.BACKUP_BUCKET, local_file, metadata_only=metadata_only)

    def _backup(self, clear_volume=False):
        JBoxVol.log_info("Backing up " + self.sessname + " at " + str(JBoxVol.BACKUP_LOC))

        bkup_file = os.path.join(JBoxVol.BACKUP_LOC, self.sessname + ".tar.gz")
        bkup_tar = tarfile.open(bkup_file, 'w:gz')

        for f in os.listdir(self.disk_path):
            if f.startswith('.') and (f in ['.juliabox']):
                continue
            full_path = os.path.join(self.disk_path, f)
            bkup_tar.add(full_path, os.path.join('juser', f))
        bkup_tar.close()
        os.chmod(bkup_file, 0666)

        if clear_volume:
            ensure_delete(self.disk_path)

        # Upload to S3 if so configured. Delete from local if successful.
        bkup_file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(bkup_file), pytz.utc) + \
            datetime.timedelta(seconds=JBoxVol.LOCAL_TZ_OFFSET)
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_BUCKETSTORE)
        if plugin is not None and JBoxVol.BACKUP_BUCKET is not None:
            if plugin.push(JBoxVol.BACKUP_BUCKET, bkup_file,
                           metadata={'backup_time': bkup_file_mtime.isoformat()}) is not None:
                os.remove(bkup_file)
                JBoxVol.log_info("Moved backup to S3 " + self.sessname)

    def restore(self):
        sessname = unique_sessname(self.user_email)
        old_sessname = esc_sessname(self.user_email)
        src = os.path.join(JBoxVol.BACKUP_LOC, sessname + ".tar.gz")
        k = JBoxVol.pull_from_bucketstore(src)  # download from S3 if exists
        if not os.path.exists(src):
            if old_sessname is not None:
                src = os.path.join(JBoxVol.BACKUP_LOC, old_sessname + ".tar.gz")
                k = JBoxVol.pull_from_bucketstore(src)  # download from S3 if exists

        if not os.path.exists(src):
            return

        JBoxVol.log_info("Filtering out restore info from backup " + src + " to " + self.disk_path)

        src_tar = tarfile.open(src, 'r:gz')
        try:
            perms = {}
            for info in src_tar.getmembers():
                if not info.name.startswith('juser/'):
                    continue
                extract_name = info.name[6:]
                if (info.type == tarfile.LNKTYPE or info.type == tarfile.SYMTYPE) and \
                        info.linkname.startswith('juser/'):
                    info.linkname = info.linkname[6:]
                if info.name.startswith('juser/.'):
                    if JBoxVol._is_path_user_home_essential(extract_name):
                        continue
                info.name = extract_name
                if len(info.name) == 0:
                    continue
                src_tar.extract(info, self.disk_path)
                extracted_path = os.path.join(self.disk_path, extract_name)
                if os.path.isdir(extracted_path) and not os.access(extracted_path, os.W_OK):
                    st = os.stat(extracted_path)
                    perms[extracted_path] = st
                    os.chmod(extracted_path, st.st_mode | stat.S_IWRITE)
            if len(perms) > 0:
                JBoxVol.log_debug("resetting permissions on %d folders", len(perms))
                for extracted_path, perm in perms.iteritems():
                    os.chmod(extracted_path, perm)
            JBoxVol.log_info("Restored backup at " + self.disk_path)
        except IOError, ioe:
            if ioe.errno == errno.ENOSPC:
                # continue login on ENOSPC to allow user to delete files
                JBoxVol.log_exception("No space left to restore backup for %s", sessname)
            else:
                raise
        finally:
            src_tar.close()
        # delete local copy of backup if we have it on bucketstore
        if k is not None:
            os.remove(src)
