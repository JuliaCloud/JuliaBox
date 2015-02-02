#! /usr/bin/env python

__author__ = 'tan'
import sys
import docker

from cloud.aws import CloudHost

from jbox_util import LoggerMixin, unique_sessname, read_config
from vol import JBoxVol, VolMgr


class S3Disk(LoggerMixin):
    @staticmethod
    def rename_and_delete(user_email):
        sessname = unique_sessname(user_email)
        renamed_sessname = sessname + '_old'
        CloudHost.move_file_in_s3(sessname + ".tar.gz", renamed_sessname + ".tar.gz", JBoxVol.BACKUP_BUCKET)

    @staticmethod
    def delete(user_email):
        sessname = unique_sessname(user_email)
        CloudHost.del_file_from_s3(JBoxVol.BACKUP_BUCKET, sessname + ".tar.gz")

    @staticmethod
    def pull_backup(user_email):
        sessname = unique_sessname(user_email)
        S3Disk.log_info("pulling %s.tar.gz from %s", sessname, JBoxVol.BACKUP_BUCKET)
        CloudHost.pull_file_from_s3(JBoxVol.BACKUP_BUCKET, sessname + ".tar.gz", metadata_only=False)

    @staticmethod
    def init():
        dckr = docker.Client()
        cfg = read_config()
        cloud_cfg = cfg['cloud_host']
        cloud_cfg['backup_bucket'] = "juliabox_userbackup"

        LoggerMixin.setup_logger(level=cfg['root_log_level'])
        LoggerMixin.DEFAULT_LEVEL = cfg['jbox_log_level']

        CloudHost.configure(has_s3=True, #cloud_cfg['s3'],
                        has_dynamodb=cloud_cfg['dynamodb'],
                        has_cloudwatch=cloud_cfg['cloudwatch'],
                        has_autoscale=cloud_cfg['autoscale'],
                        has_route53=cloud_cfg['route53'],
                        has_ebs=cloud_cfg['ebs'],
                        has_ses=cloud_cfg['ses'],
                        scale_up_at_load=cloud_cfg['scale_up_at_load'],
                        scale_up_policy=cloud_cfg['scale_up_policy'],
                        autoscale_group=cloud_cfg['autoscale_group'],
                        route53_domain=cloud_cfg['route53_domain'],
                        region=cloud_cfg['region'],
                        install_id=cloud_cfg['install_id'])

        VolMgr.configure(dckr, cfg)


def process_args(argv):
    if len(argv) < 3:
        print("Usage:")
        print("\t%s <pull> <user>" % (argv[0],))
        print("\t%s <rename> <user>" % (argv[0],))
        print("\t%s <delete> <user>" % (argv[0],))
        exit(1)
    S3Disk.init()
    cmd = argv[1]
    user = argv[2]
    if cmd == 'pull':
        S3Disk.pull_backup(user)
    # elif cmd == 'rename':
    #     S3Disk.rename_and_delete(user)
    # elif cmd == 'delete':
    #     S3Disk.delete(user)

    print("Done")


if __name__ == "__main__":
    process_args(sys.argv)