# On Ubuntu 13.04, amd64, Ubuntu provided ami image 
# ami-ef277b86

if test $# -gt 0;then
    echo 
else
    echo "Usage : ./setup.sh <admin_key> <env_only>"
    echo
    echo
    echo "Mandatory alphanumeric admin_key."
    echo "Optional env_only flag. If set (any character), no software is installed, only config/mounts are setup"
    echo
    exit
fi

if test $# -eq 1; then
    # Stuff required for docker and openresty
    sudo apt-get -y install build-essential libreadline-dev libncurses-dev libpcre3-dev libssl-dev netcat git

    # INSTALL docker as per http://docs.docker.io/en/latest/installation/ubuntulinux/
    sudo apt-get -y update
    sudo apt-get -y install linux-image-extra-`uname -r`
    sudo sh -c "wget -qO- https://get.docker.io/gpg | apt-key add -"
    sudo sh -c "echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"
    sudo apt-get -y update
    sudo apt-get -y install lxc-docker

    # docker stuff
    sudo gpasswd -a $USER docker

    # nginx
    sudo mkdir -p /tmp/resty
    sudo wget -P /tmp/resty http://openresty.org/download/ngx_openresty-1.4.3.3.tar.gz
    sudo bash -c "cd /tmp/resty; tar -xvzf ngx_openresty-1.4.3.3.tar.gz; cd ngx_openresty-1.4.3.3; ./configure ; make; make install"
    sudo rm -Rf /tmp/resty
    sudo mkdir -p /usr/local/openresty/lualib/resty/http
    sudo cp -f libs/lua-resty-http-simple/lib/resty/http/simple.lua /usr/local/openresty/lualib/resty/http/
fi

echo "Building docker image ..."
sudo docker build -t ijulia docker/IJulia/

# The below are for using the ephemeral storage available on EC2 instances for storing containers
if mount | grep /mnt/containers > /dev/null; then
    echo 
else     
    echo "bind mounting /var/lib/docker/containers and /mnt/containers ...."
    sudo mkdir -p /var/lib/docker/containers /mnt/containers
    sudo mount -o bind /mnt/containers /var/lib/docker/containers
fi

echo "Copying nginx.conf.sample to nginx.conf"
sed  s/\$\$NGINX_USER/$USER/g host/nginx/conf/nginx.conf.sample > host/nginx/conf/nginx.conf
sed  -i s/\$\$ADMIN_KEY/$1/g host/nginx/conf/nginx.conf

echo
echo "DONE!"

 
 
