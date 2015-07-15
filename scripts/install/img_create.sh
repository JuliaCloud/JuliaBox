#! /usr/bin/env bash
# Build or pull JuliaBox docker images

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

DOCKER_IMAGE=juliabox/juliabox
DOCKER_IMAGE_VER=$(grep "^# Version:" ${JBOX_DIR}/docker/Dockerfile | cut -d":" -f2)

function build_docker_image {
    echo "Building docker image ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} ..."
    sudo docker build --rm=true -t ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} docker/
    sudo docker tag -f ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} ${DOCKER_IMAGE}:latest
}

function pull_docker_image {
    echo "Pulling docker image ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} ..."
    sudo docker pull tanmaykm/juliabox:${DOCKER_IMAGE_VER}
    sudo docker tag -f tanmaykm/juliabox:${DOCKER_IMAGE_VER} ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER}
    sudo docker tag -f tanmaykm/juliabox:${DOCKER_IMAGE_VER} ${DOCKER_IMAGE}:latest
}

function make_user_home {
	${JBOX_DIR}/docker/mk_user_home.sh $1
}

if [ "$2" == "pull" ]
then
    pull_docker_image
    make_user_home $1
elif [ "$2" == "build" ]
then
    build_docker_image
    make_user_home $1
elif [ "$2" == "home" ]
then
    make_user_home $1
else
    echo "Usage: img_create.sh <data_location> <pull | build | home>"
fi

echo
echo "DONE!"
