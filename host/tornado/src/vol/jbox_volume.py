import os
import tarfile
import time
import datetime
import errno

import pytz
from cloud.aws import CloudHost

from jbox_util import LoggerMixin, unique_sessname, ensure_delete, esc_sessname, get_user_name, parse_iso_time
from jbox_crypto import ssh_keygen


class JBoxVol(LoggerMixin):
    BACKUP_LOC = None
    USER_HOME_IMG = None
    DCKR = None
    LOCAL_TZ_OFFSET = 0
    BACKUP_BUCKET = None
    NOTEBOOK_WEBSOCK_PROTO = "wss://"

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
    def configure_base(cls, dckr, wsock_proto, user_home_img, backup_loc, backup_bucket=None):
        JBoxVol.DCKR = dckr
        JBoxVol.NOTEBOOK_WEBSOCK_PROTO = wsock_proto + '://'
        JBoxVol.USER_HOME_IMG = user_home_img
        JBoxVol.BACKUP_LOC = backup_loc
        JBoxVol.LOCAL_TZ_OFFSET = JBoxVol.local_time_offset()
        JBoxVol.BACKUP_BUCKET = backup_bucket

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
            os.chmod(ssh_key_path, 0644)

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

    def restore_user_home(self):
        user_home = tarfile.open(JBoxVol.USER_HOME_IMG, 'r:gz')
        user_home.extractall(self.disk_path)
        user_home.close()

    def setup_instance_config(self):
        nbconfig = os.path.join(self.disk_path, '.ipython/profile_julia/ipython_notebook_config.py')
        nbconfig_temp = os.path.join(self.disk_path, '.ipython/profile_julia/ipython_notebook_config.py.temp')

        if os.path.exists(nbconfig_temp):
            os.remove(nbconfig_temp)
        os.rename(nbconfig, nbconfig_temp)

        wsock_cfg = "c.NotebookApp.websocket_url = '" + JBoxVol.NOTEBOOK_WEBSOCK_PROTO + \
                    CloudHost.notebook_websocket_hostname() + "'\n"

        replaced = False
        with open(nbconfig_temp) as fin, open(nbconfig, 'w') as fout:
            for line in fin:
                if line.startswith("c.NotebookApp.websocket_url"):
                    line = wsock_cfg
                    replaced = True
                fout.write(line)
            if not replaced:
                fout.write(wsock_cfg)

    @staticmethod
    def local_time_offset():
        """Return offset of local zone from GMT"""
        if time.localtime().tm_isdst and time.daylight:
            return time.altzone
        else:
            return time.timezone

    @staticmethod
    def pull_from_s3(local_file, metadata_only=False):
        if JBoxVol.BACKUP_BUCKET is None:
            return None
        return CloudHost.pull_file_from_s3(JBoxVol.BACKUP_BUCKET, local_file, metadata_only=metadata_only)

    def _backup(self, clear_volume=False):
        JBoxVol.log_info("Backing up " + self.sessname + " at " + str(JBoxVol.BACKUP_LOC))

        bkup_file = os.path.join(JBoxVol.BACKUP_LOC, self.sessname + ".tar.gz")
        bkup_tar = tarfile.open(bkup_file, 'w:gz')

        for f in os.listdir(self.disk_path):
            if f.startswith('.') and (f in ['.julia', '.ipython']):
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
        if JBoxVol.BACKUP_BUCKET is not None:
            if CloudHost.push_file_to_s3(JBoxVol.BACKUP_BUCKET, bkup_file,
                                           metadata={'backup_time': bkup_file_mtime.isoformat()}) is not None:
                os.remove(bkup_file)
                JBoxVol.log_info("Moved backup to S3 " + self.sessname)

    def restore(self):
        sessname = unique_sessname(self.user_email)
        old_sessname = esc_sessname(self.user_email)
        src = os.path.join(JBoxVol.BACKUP_LOC, sessname + ".tar.gz")
        k = JBoxVol.pull_from_s3(src)  # download from S3 if exists
        if not os.path.exists(src):
            if old_sessname is not None:
                src = os.path.join(JBoxVol.BACKUP_LOC, old_sessname + ".tar.gz")
                k = JBoxVol.pull_from_s3(src)  # download from S3 if exists

        if not os.path.exists(src):
            return

        JBoxVol.log_info("Filtering out restore info from backup " + src + " to " + self.disk_path)

        src_tar = tarfile.open(src, 'r:gz')
        try:
            for info in src_tar.getmembers():
                if not info.name.startswith('juser/'):
                    continue
                if info.name.startswith('juser/.') and (info.name.split('/')[1] in ['.juliabox', '.julia', '.ipython']):
                    continue
                info.name = info.name[6:]
                if len(info.name) == 0:
                    continue
                src_tar.extract(info, self.disk_path)
            JBoxVol.log_info("Restored backup at " + self.disk_path)
        except IOError, ioe:
            if ioe.errno == errno.ENOSPC:
                # continue login on ENOSPC to allow user to delete files
                JBoxVol.log_exception("No space left to restore backup for %s", sessname)
            else:
                raise
        finally:
            src_tar.close()
        # delete local copy of backup if we have it on s3
        if k is not None:
            os.remove(src)
