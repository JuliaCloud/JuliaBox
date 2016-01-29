#! /usr/bin/env python

__author__ = 'tan'
import sys
import os
import tarfile
import datetime
import pytz

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "engine", "src"))

from juliabox.cloud import JBPluginCloud
from juliabox.jbox_util import LoggerMixin, unique_sessname, JBoxCfg
from juliabox.vol import JBoxVol, VolMgr
from juliabox import db


class JBoxDisk(LoggerMixin):
    PLUGIN = None

    @staticmethod
    def rename_and_delete(user_email):
        sessname = unique_sessname(user_email)
        renamed_sessname = sessname + '_old'
        JBoxDisk.PLUGIN.move(sessname + ".tar.gz", renamed_sessname + ".tar.gz", JBoxVol.BACKUP_BUCKET)

    @staticmethod
    def delete(user_email):
        sessname = unique_sessname(user_email)
        JBoxDisk.PLUGIN.delete(JBoxVol.BACKUP_BUCKET, sessname + ".tar.gz")

    @staticmethod
    def pull_backup(user_email):
        sessname = unique_sessname(user_email)
        JBoxDisk.log_info("pulling %s.tar.gz from %s", sessname, JBoxVol.BACKUP_BUCKET)
        JBoxDisk.PLUGIN.pull(JBoxVol.BACKUP_BUCKET, sessname + ".tar.gz", metadata_only=False)

    @staticmethod
    def push_backup(user_email, disk_path):
        sessname = unique_sessname(user_email)
        JBoxDisk.log_info("pushing %s.tar.gz from %s to %s", sessname, disk_path, JBoxVol.BACKUP_BUCKET)

        bkup_file = os.path.join('/tmp', sessname + ".tar.gz")
        bkup_tar = tarfile.open(bkup_file, 'w:gz')

        def set_perms(tinfo):
            tinfo.uid = 1000
            tinfo.gid = 1000
            tinfo.uname = 'ubuntu'
            tinfo.gname = 'ubuntu'
            return tinfo

        for f in os.listdir(disk_path):
            if f.startswith('.') and (f in ['.julia', '.juliabox']):
                continue
            full_path = os.path.join(disk_path, f)
            bkup_tar.add(full_path, os.path.join('juser', f), filter=set_perms)
        bkup_tar.close()
        os.chmod(bkup_file, 0666)

        # Upload to cloud storage if so configured. Delete from local if successful.
        bkup_file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(bkup_file), pytz.utc) + \
            datetime.timedelta(seconds=JBoxVol.LOCAL_TZ_OFFSET)
        if JBoxVol.BACKUP_BUCKET is not None:
            if JBoxDisk.PLUGIN.push(JBoxVol.BACKUP_BUCKET, bkup_file,
                                    metadata={'backup_time': bkup_file_mtime.isoformat()}) is not None:
                os.remove(bkup_file)
                JBoxDisk.log_info("Moved backup to cloud " + sessname)

    @staticmethod
    def init():
        LoggerMixin.configure()
        db.configure()
        VolMgr.configure()
        JBoxDisk.PLUGIN = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_BUCKETSTORE)


def process_args(argv):
    if len(argv) < 3:
        print("Usage:")
        print("\t%s <pull> <user>" % (argv[0],))
        print("\t%s <push> <user> <file>" % (argv[0],))
        print("\t%s <rename> <user>" % (argv[0],))
        print("\t%s <delete> <user>" % (argv[0],))
        exit(1)
    JBoxDisk.init()
    cmd = argv[1]
    user = argv[2]
    if cmd == 'pull':
        JBoxDisk.pull_backup(user)
    elif cmd == 'push':
        JBoxDisk.push_backup(user, argv[3])
    elif cmd == 'rename':
        JBoxDisk.rename_and_delete(user)
    elif cmd == 'delete':
        JBoxDisk.delete(user)

    print("Done")


if __name__ == "__main__":
    process_args(sys.argv)
