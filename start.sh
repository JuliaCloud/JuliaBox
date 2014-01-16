#! /usr/bin/env bash
source ${PWD}/jdockcommon.sh

cp_tornado_userconf

sudo /usr/local/openresty/nginx/sbin/nginx -p ${PWD}/host/nginx    
sudo supervisord -c ${PWD}/${TORNADO_DIR}/supervisord.conf
sudo supervisorctl -c ${PWD}/${TORNADO_DIR}/supervisord.conf start all