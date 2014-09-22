#! /usr/bin/env bash
# Mount JuliaBox loopback volumes

if [ $# -ne 3 ]
then
    echo "Usage: sudo mount_fs.sh <ndisks> <ds_size_mb> <fs_user_id>"
    exit 1
fi

if [ "root" != `whoami` ]
then
    echo "Must be run as superuser"
	exit 1
fi

NDISKS=$1
FS_SIZE_MB=$2
ID=$3
echo "Creating and mounting $NDISKS user disks of size $FS_SIZE_MB MB each..."

function error_exit {
	echo "$1" 1>&2
	exit 1
}


FS_DIR=/mnt/jbox
IMG_DIR=${FS_DIR}/img
MNT_DIR=${FS_DIR}/mnt
mkdir -p ${FS_DIR} ${IMG_DIR} ${MNT_DIR} || error_exit "Could not create folders to hold filesystems"

echo "    Stopping docker to make sure no loop devices are in use..."
service docker stop

echo "Creating template disk image..."
dd if=/dev/zero of=${MNT_DIR}/jimg bs=1M count=${FS_SIZE_MB} || error_exit "Error creating disk image file"
losetup /dev/loop0 ${MNT_DIR}/jimg || error_exit "Error mapping template disk image"
mkfs -t ext3 -m 1 -v /dev/loop0 || error_exit "Error making ext3 filesystem at /dev/loop0"
chown -R ${ID}:${ID} /dev/loop0 || error_exit "Error changing file ownership on /dev/loop0"
losetup -d /dev/loop0

echo "    Creating loopback devices..."
NDISKS=$((NDISKS-1))
for i in $(seq 0 ${NDISKS})
do
    echo -n "${i}."
    LOOP=/dev/loop$i
    MNT=${MNT_DIR}/${i}
    IMG=${IMG_DIR}/${i}

    if [ ! -e $LOOP ]
    then
        mknod -m0660 $LOOP b 7 $i || error_exit "Could not create loop device $LOOP."
        chown root.disk /dev/loop$i || error_exit "Could not create loop device $LOOP. Error setting owner."
    fi

    if [ ! -e ${IMG} ]
    then
        cp ${MNT_DIR}/jimg ${IMG}
    fi
    losetup ${LOOP} ${IMG} || error_exit "Error mapping ${IMG} to ${LOOP}"

    if [ ! -e ${MNT} ]
    then
        mkdir -p ${MNT} || error_exit "Error creating mount point ${MNT}"
    fi

    mount ${LOOP} ${MNT} || error_exit "Error mounting filesystem at ${MNT}"
    chown -R ${ID}:${ID} ${MNT} || error_exit "Error changing file ownership on ${MNT}"
done

rm -f ${MNT_DIR}/jimg

echo ""
echo "DONE"
