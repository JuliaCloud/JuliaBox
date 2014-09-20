#!/bin/bash

JUSER_HOME=/tmp/juser
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

function error_exit {
	echo "$1" 1>&2
	exit 1
}

\rm -rf ${JUSER_HOME}
mkdir -p ${JUSER_HOME}
cp ${DIR}/setup_julia.sh ${JUSER_HOME}
sudo docker run -i -v ${JUSER_HOME}:/home/juser --entrypoint="/home/juser/setup_julia.sh" juliabox/juliabox:latest || error_exit "Could not run juliabox image"
rm ${JUSER_HOME}/setup_julia.sh

echo "c.NotebookApp.open_browser = False" >> ${JUSER_HOME}/.ipython/profile_julia/ipython_notebook_config.py
echo "c.NotebookApp.ip = \"*\"" >> ${JUSER_HOME}/.ipython/profile_julia/ipython_notebook_config.py
echo "c.NotebookApp.allow_origin = \"*\"" >> ${JUSER_HOME}/.ipython/profile_julia/ipython_notebook_config.py
cp docker/IJulia/custom.css ${JUSER_HOME}/.ipython/profile_julia/static/custom/custom.css

mkdir -p ${JUSER_HOME}/.juliabox

cp -R docker/IJulia/tornado ${JUSER_HOME}/.juliabox/tornado
cp docker/IJulia/supervisord.conf ${JUSER_HOME}/.juliabox/supervisord.conf

tar -czvf ~/user_home.tar.gz -C ${JUSER_HOME} .
\rm -rf ${JUSER_HOME}
