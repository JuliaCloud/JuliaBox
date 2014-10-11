#!/bin/bash

JUSER_HOME=/tmp/juser
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SUDO_JUSER="sudo -u 1000 -g 1000"

function error_exit {
	echo "$1" 1>&2
	exit 1
}

sudo rm -rf ${JUSER_HOME}
mkdir -p ${JUSER_HOME}
cp ${DIR}/setup_julia.sh ${JUSER_HOME}
sudo chown -R 1000:1000 ${JUSER_HOME}
sudo docker run -i -v ${JUSER_HOME}:/home/juser --entrypoint="/home/juser/setup_julia.sh" juliabox/juliabox:latest || error_exit "Could not run juliabox image"
${SUDO_JUSER} rm ${JUSER_HOME}/setup_julia.sh

${SUDO_JUSER} echo "c.NotebookApp.open_browser = False" >> ${JUSER_HOME}/.ipython/profile_julia/ipython_notebook_config.py
${SUDO_JUSER} echo "c.NotebookApp.ip = \"*\"" >> ${JUSER_HOME}/.ipython/profile_julia/ipython_notebook_config.py
${SUDO_JUSER} echo "c.NotebookApp.allow_origin = \"*\"" >> ${JUSER_HOME}/.ipython/profile_julia/ipython_notebook_config.py
${SUDO_JUSER} cp ${DIR}/IJulia/custom.css ${JUSER_HOME}/.ipython/profile_julia/static/custom/custom.css

${SUDO_JUSER} mkdir -p ${JUSER_HOME}/.juliabox

${SUDO_JUSER} cp -R ${DIR}/IJulia/tornado ${JUSER_HOME}/.juliabox/tornado
${SUDO_JUSER} cp ${DIR}/IJulia/supervisord.conf ${JUSER_HOME}/.juliabox/supervisord.conf

sudo rm ~/user_home.tar.gz
sudo tar -czvf ~/user_home.tar.gz -C ${JUSER_HOME} .
sudo rm -rf ${JUSER_HOME}
