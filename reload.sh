#! /usr/bin/env bash
source ${PWD}/jboxcommon.sh

cp_tornado_userconf

sudo supervisorctl -c ${PWD}/host/supervisord.conf restart all
