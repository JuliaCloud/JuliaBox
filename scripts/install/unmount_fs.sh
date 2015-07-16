#! /usr/bin/env bash
# Remove and delete JuliaBox mounted loopback volumes

if [ $# -ne 2 ]
then
    echo "Usage: sudo unmount_fs.sh <data_location> [delete fstab entries and files (0/1)]"
    exit 1
fi

if [ "root" != `whoami` ]
then
    echo "Must be run as superuser"
	exit 1
fi

DATA_LOC=$1
FS_DIR=${DATA_LOC}/disks
LOOP_IMG_DIR=${FS_DIR}/loop/img
LOOP_MNT_DIR=${FS_DIR}/loop/mnt
EBS_DIR=${FS_DIR}/ebs


function error_exit {
	echo "$1" 1>&2
	exit 1
}

function rm_ebs_fstab_entries {
    grep -v "$1" /etc/fstab > /tmp/tmpfstab
    cp /etc/fstab /tmp/fstab.bak
    cat /tmp/tmpfstab > /etc/fstab
}

echo "Unmounting..."
jbox_mounts=`mount | grep $LOOP_MNT_DIR | cut -d" " -f3`
jbox_devs=`mount | grep $LOOP_MNT_DIR | cut -d" " -f1`

for m in $jbox_mounts
do
    sudo umount $m || error_exit "Error unmounting $m"
done

for l in $jbox_devs
do
    sudo losetup -d $l || error_exit "Error deleting $l"
done

if [ "$2" -eq 1 ]
then
    echo "Deleting files from ${FS_DIR}..."
    sudo \rm -rf ${FS_DIR}/*
    echo "Deleting fstab entries..."
    rm_ebs_fstab_entries ${EBS_DIR}
fi
