#! /usr/bin/env bash
# Clean all logs

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

\rm -f ${JBOX_DIR}/host/run/*.log
\rm -f ${JBOX_DIR}/host/nginx/logs/*.log
\rm -f ${JBOX_DIR}/host/tornado/logs/*.log
