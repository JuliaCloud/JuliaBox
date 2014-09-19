#! /usr/bin/env bash
# Build or pull JuliaBox docker images

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

DOCKER_IMAGE=juliabox/juliabox
DOCKER_IMAGE_VER=$(grep "^# Version:" docker/IJulia/Dockerfile | cut -d":" -f2)

function build_docker_image {
    echo "Building docker image ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} ..."
    sudo docker build --rm=true -t ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} docker/IJulia/
    sudo docker tag ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} ${DOCKER_IMAGE}:latest
}

function pull_docker_image {
    echo "Pulling docker image ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} ..."
    sudo docker pull tanmaykm/juliabox:${DOCKER_IMAGE_VER}
    sudo docker tag tanmaykm/juliabox:${DOCKER_IMAGE_VER} ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER}
    sudo docker tag tanmaykm/juliabox:${DOCKER_IMAGE_VER} ${DOCKER_IMAGE}:latest
}

function make_user_home {
	${JBOX_DIR}/docker/mk_user_home.sh
}

if [ "$1" == "pull" ]
then
    pull_docker_image
    make_user_home
elif [ "$1" == "build" ]
then
    build_docker_image
    make_user_home
elif [ "$1" == "home" ]
then
    make_user_home
else
    echo "Usage: img_create.sh <pull | build | home>"
fi

echo
echo "DONE!"
