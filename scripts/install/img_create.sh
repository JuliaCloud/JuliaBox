#! /usr/bin/env bash
# Build or pull JuliaBox docker images

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

function build_web_engines {
    for pycfile in `find ${JBOX_DIR} -name "*.pyc" -print`
    do
        sudo rm $pycfile
    done

    for imgspec in webserver,webserver/Dockerfile enginebase,engine/Dockerfile.base enginedaemon,engine/Dockerfile.daemon engineinteractive,engine/Dockerfile.interactive engineapi,engine/Dockerfile.api
    do
        IFS=","
        set ${imgspec}
        IMGTAG="juliabox/$1"
        DOCKERFILE=${JBOX_DIR}/$2
        DOCKERDIR=$(dirname ${DOCKERFILE})
        echo ""
        echo "======================================================"
        echo "Building docker image ${IMGTAG} from ${DOCKERFILE} ..."
        echo "======================================================"
        docker build -t ${IMGTAG} -f ${DOCKERFILE} ${DOCKERDIR}
        unset IFS
    done
}

function build_containers {
    for imgspec in juliabox,docker juliaboxapi,container/api
    do
        IFS=","
        set ${imgspec}
        IMGTAG="juliabox/$1"
        DOCKERDIR=${JBOX_DIR}/$2/
        IMGVER=$(grep "^# Version:" ${DOCKERDIR}/Dockerfile | cut -d":" -f2)
        echo ""
        echo "======================================================"
        echo "Building container ${IMGTAG}:${IMGVER} from ${DOCKERDIR} ..."
        echo "======================================================"
        docker build -t ${IMGTAG}:${IMGVER} -f ${DOCKERDIR}/Dockerfile ${DOCKERDIR}
        docker tag -f ${IMGTAG}:${IMGVER} ${IMGTAG}:latest
    done
}

function pull_containers {
    for imgspec in juliabox,docker juliaboxapi,container/api
    do
        IFS=","
        set ${imgspec}
        IMGTAG="juliabox/$1"
        PULLIMGTAG="tanmaykm/$1"
        DOCKERDIR=${JBOX_DIR}/$2
        IMGVER=$(grep "^# Version:" ${DOCKERDIR}/Dockerfile | cut -d":" -f2)
        echo ""
        echo "======================================================"
        echo "Pulling container ${IMGTAG}:${IMGVER}..."
        echo "======================================================"
        docker pull -t ${PULLIMGTAG}:${IMGVER}
        docker tag -f ${PULLIMGTAG}:${IMGVER} ${IMGTAG}:${IMGVER}
        docker tag -f ${IMGTAG}:${IMGVER} ${IMGTAG}:latest
    done
}

function make_user_home {
	${JBOX_DIR}/docker/mk_user_home.sh $1
}

function print_usage {
    echo "Usage:"
    echo "Build JulaiBox components: img_create.sh jbox"
    echo "Build/Pull JulaiBox containers: img_create.sh cont <build | pull>"
    echo "Build pkg bundle and user home image: img_create.sh home <data_location>"
}

cmd=$1
cmdparam=$2

if [ "$cmd" == "cont" ]; then
    if [ "$cmdparam" == "pull" ]; then
        pull_containers
    elif [ "$cmdparam" == "build" ]; then
        build_containers
    else
        print_usage
    fi
elif [ "$cmd" == "home" ]; then
    make_user_home "$cmdparam"
elif [ "$cmd" == "jbox" ]; then
    build_web_engines
else
    print_usage
fi

echo
echo "DONE!"
