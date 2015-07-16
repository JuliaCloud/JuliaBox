#! /usr/bin/env bash
# Restart JuliaBox server

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

sudo supervisorctl -c ${PWD}/host/supervisord.conf restart all
