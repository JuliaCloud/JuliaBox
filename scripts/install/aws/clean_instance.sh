#! /usr/bin/env bash
# Clean up the EC2 instance before building an AMI

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source ${DIR}/../../jboxcommon.sh

if [ "root" != `whoami` ]
then
    echo "Must be run as superuser"
    exit 1
fi

${JBOX_DIR}/scripts/run/stop.sh
${JBOX_DIR}/scripts/run/clean.sh

\rm -f ${WEBSERVER_CONF_DIR}/conf/nginx.conf
\rm -f ${ENGINE_CONF_DIR}/tornado.conf
\rm -f ${ENGINE_CONF_DIR}/jbox.user

\rm -f ${ENGINE_CONF_DIR}/.boto
\rm -f ${JBOX_DIR}/.jbox_session_key

${JBOX_DIR}/scripts/install/unmount_fs.sh /jboxengine/data 1

truncate -s 0 .bash_history
truncate -s 0 /var/awslogs/etc/aws.conf

for id in `docker ps -a | cut -d" " -f1 | grep -v CONTAINER`; do echo $id; docker kill $id; docker rm $id; done
service docker stop
cp /jboxengine/data/julia_packages.tar.gz ~/julia_packages.tar.gz
cp /jboxengine/data/user_home.tar.gz ~/user_home.tar.gz
umount /jboxengine