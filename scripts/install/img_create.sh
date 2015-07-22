#! /usr/bin/env bash
# Build or pull JuliaBox docker images

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

DOCKER_IMAGE=juliabox/juliabox
DOCKER_IMAGE_VER=$(grep "^# Version:" ${JBOX_DIR}/docker/Dockerfile | cut -d":" -f2)

function build_web_engines {
    for pycfile in `find ${JBOX_DIR} -name "*.pyc" -print`
    do
        sudo rm $pycfile
    done

    for imgspec in webserver,webserver/Dockerfile enginebase,engine/Dockerfile.base enginedaemon,engine/Dockerfile.daemon engineinteractive,engine/Dockerfile.interactive
    do
        IFS=","
        set ${imgspec}
        IMGTAG="juliabox/$1"
        DOCKERFILE=${JBOX_DIR}/$2
        DOCKERDIR=$(dirname ${DOCKERFILE})
        echo "Building docker image ${IMGTAG} from ${DOCKERFILE} ..."
        sudo docker build -t ${IMGTAG} -f ${DOCKERFILE} ${DOCKERDIR}
        unset IFS
    done
}

function build_docker_image {
    echo "Building docker image ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} ..."
    sudo docker build --rm=true -t ${DOCKER_IMAGE}:${DOCKER_IMAGE_VER} ${JBOX_DIR}/docker/
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

cmd=$1
dataloc=$2

if [ "$cmd" == "pull" ]
then
    pull_docker_image
    make_user_home "$dataloc"
elif [ "$cmd" == "build" ]
then
    build_docker_image
    make_user_home "$dataloc"
elif [ "$cmd" == "home" ]
then
    make_user_home "$dataloc"
elif [ "$cmd" == "jbox" ]
then
    build_web_engines
else
    echo "Usage: img_create.sh <pull | build | home | jbox> <data_location>"
fi

echo
echo "DONE!"
