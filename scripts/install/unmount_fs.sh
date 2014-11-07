#! /usr/bin/env bash
# Remove and delete JuliaBox mounted loopback volumes

FS_DIR=/mnt/jbox
IMG_DIR=${FS_DIR}/img
MNT_DIR=${FS_DIR}/mnt
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
jbox_mounts=`mount | grep "/mnt/jbox/mnt" | cut -d" " -f3`
jbox_devs=`mount | grep "/mnt/jbox/mnt" | cut -d" " -f1`

for m in $jbox_mounts
do
    sudo umount $m || error_exit "Error unmounting $m"
done

for l in $jbox_devs
do
    sudo losetup -d $l || error_exit "Error deleting $l"
done

if [ "$1" == "del" ]
then
    echo "Deleting files..."
    sudo \rm -rf /mnt/jbox/*
    echo "Deleting fstab entries..."
    rm_ebs_fstab_entries ${EBS_DIR}
fi
