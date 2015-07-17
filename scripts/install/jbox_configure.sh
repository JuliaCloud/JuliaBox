#! /usr/bin/env bash
# Configure JuliaBox components

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source ${DIR}/../jboxcommon.sh

function gen_sesskey {
    echo "Generating random session validation key"
    SESSKEY=`< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c32`
    echo $SESSKEY > ${HOST_DIR}/.jbox_session_key
}

function configure_resty_tornado {
    echo "Setting up webserver and engine configurations..."
    sed  s/\$\$SESSKEY/$SESSKEY/g $WEBSERVER_CONF_DIR/nginx.conf.tpl > $WEBSERVER_CONF_DIR/nginx.conf
    sed  s/\$\$SESSKEY/$SESSKEY/g $ENGINE_CONF_DIR/tornado.conf.tpl > $ENGINE_CONF_DIR/tornado.conf
}

if [ ! -e ${HOST_DIR}/.jbox_session_key ]
then
    gen_sesskey
fi
SESSKEY=`cat ${HOST_DIR}/.jbox_session_key`

configure_resty_tornado

echo
echo "DONE!"