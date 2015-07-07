#! /usr/bin/env bash
# Stop JuliaBox server

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

sudo supervisorctl -c ${JBOX_DIR}/host/supervisord.conf stop all
sudo supervisorctl -c ${JBOX_DIR}/host/supervisord.conf shutdown
docker rm webserver_jboxsvc
