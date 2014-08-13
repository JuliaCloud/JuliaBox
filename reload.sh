#! /usr/bin/env bash
source ${PWD}/jdockcommon.sh

cp_tornado_userconf

sudo supervisorctl -c ${PWD}/host/supervisord.conf restart all
