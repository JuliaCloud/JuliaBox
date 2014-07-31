#! /usr/bin/env bash
# JuliaBox utility script to:
# - restore container backups from host
# - generate ssh keys for user

BKP=/juliabox/restore.tar.gz
JH=$HOME
#BKP=./restore.tar.gz
#JH=.

function restore_backup {
    if [ -f $BKP ]
    then
        tar -xzvf $BKP
        rm -f $BKP
    fi
}

# restore container backups if provided
restore_backup

# generate ssh keys the first time (old keys are restored back in the step before)
if [ ! -f ${JH}/.ssh/id_rsa ]
then
    mkdir -p ${JH}/.ssh
    ssh-keygen -q -t rsa -N "" -C "juliabox" -f ${JH}/.ssh/id_rsa > ${JH}/.ssh/id_rsa.pub
    chmod 700 ${JH}/.ssh
    chmod 600 ${JH}/.ssh/id_rsa
    chmod 644 ${JH}/.ssh/id_rsa.pub
fi

while true
do
    # TODO: use inotify-tools
    sleep 300
    restore_backup
done

