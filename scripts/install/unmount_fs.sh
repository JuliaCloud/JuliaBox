#! /usr/bin/env bash
# Remove and delete JuliaBox mounted loopback volumes

FS_DIR=/mnt/jbox
IMG_DIR=${FS_DIR}/img
MNT_DIR=${FS_DIR}/mnt

function error_exit {
	echo "$1" 1>&2
	exit 1
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

echo "Deleting files..."
sudo \rm -rf /mnt/jbox/*
