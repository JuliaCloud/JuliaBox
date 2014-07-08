sudo ${PWD}/host/install/openresty/nginx/sbin/nginx -p ${PWD}/host/nginx -s stop
sudo supervisorctl -c ${PWD}/host/tornado/supervisord.conf stop all
sudo supervisorctl -c ${PWD}/host/tornado/supervisord.conf shutdown
