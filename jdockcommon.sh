TORNADO_DIR=host/tornado
TORNADO_CONF_DIR=$TORNADO_DIR/conf

NGINX_DIR=host/nginx
NGINX_CONF_DIR=$NGINX_DIR/conf

function cp_tornado_userconf {
    # copy user configuration files to appropriate places
    if [ -e "jdock.user" ]
    then
        cp -f ${PWD}/jdock.user ${PWD}/${TORNADO_DIR}/conf
    else
        rm -f ${PWD}/${TORNADO_CONF_DIR}/jdock.user
    fi
}