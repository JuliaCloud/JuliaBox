#! /usr/bin/env bash
# Start JuliaBox server

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

sudo supervisord -c ${JBOX_DIR}/host/supervisord.conf
sudo supervisorctl -c ${JBOX_DIR}/host/supervisord.conf start all
