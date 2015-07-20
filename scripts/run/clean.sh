#! /usr/bin/env bash
# Clean all logs

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source ${DIR}/../jboxcommon.sh

\rm -f ${HOST_DIR}/run/*.log
\rm -f ${WEBSERVER_DIR}/logs/*.log
\rm -f ${ENGINE_DIR}/logs/*.log

\rm -f ${HOST_DIR}/run/*.log.?
\rm -f ${WEBSERVER_DIR}/logs/*.log.?
\rm -f ${ENGINE_DIR}/logs/*.log.?
