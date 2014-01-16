#! /usr/bin/env bash
source ${PWD}/jdockcommon.sh

cp_tornado_userconf

sudo /usr/local/openresty/nginx/sbin/nginx -p ${PWD}/host/nginx -s reload
sudo supervisorctl -c ${PWD}/host/tornado/supervisord.conf restart all
