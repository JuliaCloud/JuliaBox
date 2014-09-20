#! /usr/bin/env bash
# Mount JuliaBox loopback volumes

if [ $# -ne 2 ]
then
    echo "Usage: sudo mount_fs.sh <ndisks> <ds_size_mb>"
    exit 1
fi

NDISKS=$1
FS_SIZE_MB=$2
ID=`whoami`
echo "Creating and mounting $NDISKS user disks of size $FS_SIZE_MB MB each..."

function error_exit {
	echo "$1" 1>&2
	exit 1
}


FS_DIR=/mnt/jbox
IMG_DIR=${FS_DIR}/img
MNT_DIR=${FS_DIR}/mnt
sudo mkdir -p ${FS_DIR} ${IMG_DIR} ${MNT_DIR} || error_exit "Could not create folders to hold filesystems"

echo "    Stopping docker to make sure no loop devices are in use..."
sudo service docker stop

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
        sudo mknod -m0660 $LOOP b 7 $i || error_exit "Could not create loop device $LOOP."
        sudo chown root.disk /dev/loop$i || error_exit "Could not create loop device $LOOP. Error setting owner."
    fi

    if [ ! -e ${IMG} ]
    then
        sudo dd if=/dev/zero of=${IMG} bs=1024 count=${FS_SIZE_MB}000 || error_exit "Error creating disk image file"
        sudo losetup ${LOOP} ${IMG} || error_exit "Error mapping ${IMG} to ${LOOP}"
        sudo mkfs -t ext3 -m 1 -v ${LOOP} || error_exit "Error making ext3 filesystem at ${LOOP}"
    else
        sudo losetup ${LOOP} ${IMG} || error_exit "Error mapping ${IMG} to ${LOOP}"
    fi

    if [ ! -e ${MNT} ]
    then
        sudo mkdir -p ${MNT} || error_exit "Error creating mount point ${MNT}"
    fi

    sudo mount ${LOOP} ${MNT} || error_exit "Error mounting filesystem at ${MNT}"
    sudo chown -R ${ID}:${ID} ${MNT} || error_exit "Error changing file ownership on ${MNT}"
done

