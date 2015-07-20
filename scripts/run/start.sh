#! /usr/bin/env bash
# Start JuliaBox server

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source ${DIR}/../jboxcommon.sh

sudo supervisord -c ${HOST_DIR}/supervisord.conf
sudo supervisorctl -c ${HOST_DIR}/supervisord.conf start all
