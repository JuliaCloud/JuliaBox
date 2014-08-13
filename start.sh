#! /usr/bin/env bash
source ${PWD}/jdockcommon.sh

cp_tornado_userconf

sudo supervisord -c ${PWD}/host/supervisord.conf
sudo supervisorctl -c ${PWD}/host/supervisord.conf start all
