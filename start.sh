# On EC2 the ephemeral mounts disappear on system stop/start
if mount | grep /mnt/containers > /dev/null; then
    echo 
else     
    echo "bind mounting /var/lib/docker/containers and /mnt/containers ...."
    sudo mkdir -p /var/lib/docker/containers /mnt/containers
    sudo mount -o bind /mnt/containers /var/lib/docker/containers
fi


sudo /usr/local/openresty/nginx/sbin/nginx -p ${PWD}/host/nginx    
sudo supervisord -c ${PWD}/host/tornado/supervisord.conf
sudo supervisorctl -c ${PWD}/host/tornado/supervisord.conf start all