DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/..`

ENGINE_DIR=${JBOX_DIR}/engine
ENGINE_CONF_DIR=${ENGINE_DIR}/conf

WEBSERVER_DIR=${JBOX_DIR}/webserver
WEBSERVER_CONF_DIR=${WEBSERVER_DIR}/conf

HOST_DIR=${JBOX_DIR}/host