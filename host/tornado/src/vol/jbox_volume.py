import os
import tarfile
import time

from jbox_util import LoggerMixin, CloudHelper
from jbox_crypto import ssh_keygen


class JBoxVol(LoggerMixin):
    USER_HOME_IMG = None
    DCKR = None
    LOCAL_TZ_OFFSET = 0

    def __init__(self, disk_path, user_name, user_email):
        self.disk_path = disk_path
        self.user_name = user_name
        self.user_email = user_email
        self._dbg_str = str(user_name) + " (" + str(user_email) + ") " + disk_path

    @classmethod
    def dckr(cls):
        return JBoxVol.DCKR

    @classmethod
    def tz_offset(cls):
        return JBoxVol.LOCAL_TZ_OFFSET

    @classmethod
    def configure_base(cls, dckr, user_home_img):
        JBoxVol.DCKR = dckr
        JBoxVol.USER_HOME_IMG = user_home_img
        JBoxVol.LOCAL_TZ_OFFSET = JBoxVol.local_time_offset()

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

    def restore_user_home(self):
        user_home = tarfile.open(JBoxVol.USER_HOME_IMG, 'r:gz')
        user_home.extractall(self.disk_path)
        user_home.close()

    def setup_instance_config(self):
        nbconfig = os.path.join(self.disk_path, '.ipython/profile_julia/ipython_notebook_config.py')
        with open(nbconfig, "a") as nbconfig_file:
            nbconfig_file.write(
                "c.NotebookApp.websocket_url = 'wss://" + CloudHelper.notebook_websocket_hostname() + "'\n")

    @staticmethod
    def local_time_offset():
        """Return offset of local zone from GMT"""
        if time.localtime().tm_isdst and time.daylight:
            return time.altzone
        else:
            return time.timezone
