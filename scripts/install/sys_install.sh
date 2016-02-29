#! /usr/bin/env bash
# Install base system packages required for JuliaBox
# On Ubuntu 14.04, amd64, Ubuntu provided ami image 
# ami-80778be8

# configure docker to use either AUFS or DEVICEMAPPER
#DOCKER_FS=AUFS
DOCKER_FS=DEVICEMAPPER
NUM_LOCALMAX=30

function sysinstall_pystuff {
    sudo easy_install tornado
    sudo easy_install futures
    sudo easy_install google-api-python-client
    sudo pip install PyDrive
    sudo pip install boto
    sudo pip install pycrypto
    sudo pip install psutil
    sudo pip install cli53
    sudo pip install sh
    sudo pip install pyzmq
    sudo pip install docker-py
    sudo pip install MySQL-python
}

function sysinstall_libs {
    # Stuff required for docker, and tornado
    sudo apt-get -y update
    sudo apt-get -y install build-essential libreadline-dev libncurses-dev libpcre3-dev libssl-dev netcat git python-setuptools supervisor python-dev python-isodate python-pip python-tz libzmq-dev
}

function sysinstall_docker {
    wget -qO- https://get.docker.com/ | sh
    sudo usermod -aG docker $USER
}

function configure_docker {
    # Devicemapper storage can be used if disk quotas are desired. However it is less stable than aufs.
    sudo service docker stop
    if grep -q "^DOCKER_OPTS" /etc/default/docker
    then
        echo "/etc/default/docker has an entry for DOCKER_OPTS..."
        echo "Please ensure DOCKER_OPTS has appropriate options"
    elif [ "$DOCKER_FS" == "DEVICEMAPPER" ]
    then
        # set loop data size to that required for max containers plus 5 additional
        LOOPDATASZ=$(((NUM_LOCALMAX+5)*6))
        echo "Configuring docker to use"
        echo "    - devicemapper fs"
        echo "    - base image size 7GB"
        echo "    - loopdatasize ${LOOPDATASZ}GB"
        sudo sh -c "echo 'DOCKER_OPTS=\"--storage-driver=devicemapper --storage-opt dm.basesize=7G --storage-opt dm.loopdatasize=${LOOPDATASZ}G\"' >> /etc/default/docker"
    else
        echo "Configuring docker to use aufs"
        sudo sh -c "echo 'DOCKER_OPTS=\"--storage-driver=aufs\"' >> /etc/default/docker"
    fi
    sudo service docker start

    # Wait for the docker process to bind to the required ports
    sleep 1
}

sysinstall_libs
sysinstall_docker
sysinstall_pystuff
configure_docker
echo
echo "DONE!"
 
