#! /usr/bin/env bash
# Restart JuliaBox server

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source ${DIR}/../jboxcommon.sh

sudo supervisorctl -c ${HOST_DIR}/supervisord.conf restart all
