import os
import tarfile
import datetime
import pytz

from jbox_util import CloudHelper, ensure_delete, unique_sessname, esc_sessname, get_user_name
from jbox_volume import JBoxVol


class JBoxLoopbackVol(JBoxVol):
    FS_LOC = None
    BACKUP_LOC = None
    DISK_LIMIT = None
    BACKUP_BUCKET = None
    MAX_CONTAINERS = 0
    MAX_DISKS = 0
    VALID_CONTAINERS = {}
    DISK_USE_STATUS = {}

    def __init__(self, disk_path, user_name, user_email):
        super(JBoxLoopbackVol, self).__init__(disk_path, user_name, user_email)

    @staticmethod
    def configure(disk_limit, fs_loc, backup_loc, max_disks, backup_bucket=None):
        JBoxLoopbackVol.FS_LOC = fs_loc
        JBoxLoopbackVol.BACKUP_LOC = backup_loc
        JBoxLoopbackVol.DISK_LIMIT = disk_limit
        JBoxLoopbackVol.BACKUP_BUCKET = backup_bucket
        JBoxLoopbackVol.MAX_DISKS = max_disks
        JBoxLoopbackVol.refresh_disk_use_status()

    @classmethod
    def get_disk_allocated_size(cls):
        return JBoxLoopbackVol.DISK_LIMIT

    @staticmethod
    def get_disk_ids_used(cid):
        used = []
        props = JBoxLoopbackVol.dckr().inspect_container(cid)
        try:
            vols = props['Volumes']
            for _cpath, hpath in vols.iteritems():
                if hpath.startswith(JBoxLoopbackVol.FS_LOC):
                    used.append(int(hpath.split('/')[-1]))
        except:
            JBoxLoopbackVol.log_error("error finding disk ids used in " + cid)
            return []
        return used

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        for idx in range(0, JBoxLoopbackVol.MAX_DISKS):
            JBoxLoopbackVol.DISK_USE_STATUS[idx] = False

        nfree = JBoxLoopbackVol.MAX_DISKS
        if container_id_list is None:
            container_id_list = JBoxLoopbackVol.dckr().containers(all=True)

        for cdesc in container_id_list:
            cid = cdesc['Id']
            disk_ids = JBoxLoopbackVol.get_disk_ids_used(cid)
            for disk_id in disk_ids:
                JBoxLoopbackVol.mark_disk_used(disk_id)
                nfree -= 1
        JBoxLoopbackVol.log_info("Disk free: " + str(nfree) + "/" + str(JBoxLoopbackVol.MAX_DISKS))

    @staticmethod
    def disk_ids_used_pct():
        pct = (sum(JBoxLoopbackVol.DISK_USE_STATUS.values()) * 100) / len(JBoxLoopbackVol.DISK_USE_STATUS)
        return min(100, max(0, pct))

    @staticmethod
    def get_unused_disk_id():
        for idx in range(0, JBoxLoopbackVol.MAX_DISKS):
            if not JBoxLoopbackVol.DISK_USE_STATUS[idx]:
                return idx
        return -1

    @staticmethod
    def mark_disk_used(idx, used=True):
        JBoxLoopbackVol.DISK_USE_STATUS[idx] = used

    @staticmethod
    def get_disk_for_user(user_email):
        disk_id = JBoxLoopbackVol.get_unused_disk_id()
        if disk_id < 0:
            raise Exception("No free disk available")
        disk_path = os.path.join(JBoxLoopbackVol.FS_LOC, str(disk_id))
        ensure_delete(disk_path)
        loopvol = JBoxLoopbackVol(disk_path, get_user_name(user_email), user_email)

        loopvol.restore_user_home()
        loopvol.setup_instance_config()
        loopvol.restore_backup_to_disk()
        return loopvol

    def restore_backup_to_disk(self):
        sessname = unique_sessname(self.user_email)
        old_sessname = esc_sessname(self.user_email)
        src = os.path.join(JBoxLoopbackVol.BACKUP_LOC, sessname + ".tar.gz")
        k = JBoxLoopbackVol.pull_from_s3(src)  # download from S3 if exists
        if not os.path.exists(src):
            if old_sessname is not None:
                src = os.path.join(JBoxLoopbackVol.BACKUP_LOC, old_sessname + ".tar.gz")
                k = JBoxLoopbackVol.pull_from_s3(src)  # download from S3 if exists

        if not os.path.exists(src):
            return

        JBoxLoopbackVol.log_info("Filtering out restore info from backup " + src + " to " + self.disk_path)

        src_tar = tarfile.open(src, 'r:gz')
        for info in src_tar.getmembers():
            if not info.name.startswith('juser/'):
                continue
            if info.name.startswith('juser/.') and (info.name.split('/')[1] in ['.juliabox', '.julia', '.ipython']):
                continue
            info.name = info.name[6:]
            if len(info.name) == 0:
                continue
            src_tar.extract(info, self.disk_path)
        src_tar.close()
        JBoxLoopbackVol.log_info("Restored backup at " + self.disk_path)
        # delete local copy of backup if we have it on s3
        if k is not None:
            os.remove(src)

    @staticmethod
    def backup(sessname, cid):
        JBoxLoopbackVol.log_info("Backing up " + sessname + " at " + str(JBoxLoopbackVol.BACKUP_LOC))

        bkup_file = os.path.join(JBoxLoopbackVol.BACKUP_LOC, sessname + ".tar.gz")

        disk_ids_used = JBoxLoopbackVol.get_disk_ids_used(cid)
        disk_id_used = disk_ids_used[0]
        disk_path = os.path.join(JBoxLoopbackVol.FS_LOC, str(disk_id_used))
        bkup_tar = tarfile.open(bkup_file, 'w:gz')

        for f in os.listdir(disk_path):
            if f.startswith('.') and (f in ['.julia', '.ipython']):
                continue
            full_path = os.path.join(disk_path, f)
            bkup_tar.add(full_path, os.path.join('juser', f))
        bkup_tar.close()
        os.chmod(bkup_file, 0666)
        ensure_delete(disk_path)

        # Upload to S3 if so configured. Delete from local if successful.
        bkup_file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(bkup_file), pytz.utc) + \
            datetime.timedelta(seconds=JBoxLoopbackVol.tz_offset())
        if JBoxLoopbackVol.BACKUP_BUCKET is not None:
            if CloudHelper.push_file_to_s3(JBoxLoopbackVol.BACKUP_BUCKET, bkup_file,
                                           metadata={'backup_time': bkup_file_mtime.isoformat()}) is not None:
                os.remove(bkup_file)
                JBoxLoopbackVol.log_info("Moved backup to S3 " + sessname)

    @staticmethod
    def pull_from_s3(local_file, metadata_only=False):
        if JBoxLoopbackVol.BACKUP_BUCKET is None:
            return None
        return CloudHelper.pull_file_from_s3(JBoxLoopbackVol.BACKUP_BUCKET, local_file, metadata_only=metadata_only)
