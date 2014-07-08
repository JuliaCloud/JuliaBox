#! /usr/bin/env bash
# Setup for development. Only build nginx openresty and instal onto host/install folder.
# Assumes all other required packages have been installed manually using appropriate apt-get / pip commands.
# Tested on Ubuntu 14.04

source ${PWD}/jdockcommon.sh
NGINX_VER=1.7.0.1
NGINX_INSTALL_DIR=${PWD}/host/install/openresty
mkdir -p $NGINX_INSTALL_DIR


function usage {
  echo
  echo 'Usage: ./setup.sh -u <admin_username> optional_args'
  echo ' -u  <username> : Mandatory admin username. If -g option is used, this must be the complete Google email-id'
  echo ' -d             : Only recreate docker image - do not install/update other software'
  echo ' -g             : Use Google OAuth2 for user authentication. Options -k and -s must be specified.'
  echo ' -n  <num>      : Maximum number of active containers. Deafult 10.'
  echo ' -t  <seconds>  : Auto delete containers older than specified seconds. 0 means never expire. Default 0.'
  echo ' -k  <key>      : Google OAuth2 key (client id).'
  echo ' -s  <secret>   : Google OAuth2 client secret.'
  echo
  echo 'Post setup, additional configuration parameters may be set in jdock.user '
  echo 'Please see README.md for more details '
  
  exit 1
}

OPT_INSTALL=1
OPT_GOOGLE=0
NUM_LOCALMAX=10 
EXPIRE=0

while getopts  "u:dgn:t:k:s:" FLAG
do
  if test $FLAG == '?'
     then
        usage

  elif test $FLAG == 'u'
     then
        ADMIN_USER=$OPTARG

  elif test $FLAG == 'd'
     then
        OPT_INSTALL=0

  elif test $FLAG == 'g'
     then
        OPT_GOOGLE=1

  elif test $FLAG == 'n'
     then
        NUM_LOCALMAX=$OPTARG

  elif test $FLAG == 't'
     then
        EXPIRE=$OPTARG

  elif test $FLAG == 'k'
     then
        CLIENT_ID=$OPTARG

  elif test $FLAG == 's'
     then
        CLIENT_SECRET=$OPTARG
  fi
done

if test -v $ADMIN_USER
  then
    usage
fi

#echo $ADMIN_USER $OPT_INSTALL $OPT_GOOGLE


if test $OPT_INSTALL -eq 1; then
    echo "Building nginx openresty for install at ${NGINX_INSTALL_DIR} ..."
    # nginx
    mkdir -p /tmp/resty

    # keep a local copy of nginx sources 
    if [ -e ngx_openresty-${NGINX_VER}.tar.gz ]
    then
        cp ngx_openresty-${NGINX_VER}.tar.gz /tmp/resty/
    else
        wget -P /tmp/resty http://openresty.org/download/ngx_openresty-${NGINX_VER}.tar.gz
        cp /tmp/resty/ngx_openresty-${NGINX_VER}.tar.gz .
    fi

    bash -c "cd /tmp/resty; tar -xvzf ngx_openresty-${NGINX_VER}.tar.gz; cd ngx_openresty-${NGINX_VER}; ./configure --prefix=${NGINX_INSTALL_DIR}; make; make install"
    rm -Rf /tmp/resty
    mkdir -p ${NGINX_INSTALL_DIR}/lualib/resty/http
    cp -f libs/lua-resty-http-simple/lib/resty/http/simple.lua ${NGINX_INSTALL_DIR}/lualib/resty/http/
fi

DOCKER_IMAGE=dev_${USER}/ijulia
echo "Building docker image ${DOCKER_IMAGE} ..."
docker build -t ${DOCKER_IMAGE} docker/IJulia/

echo "Setting up nginx.conf ..."
sed  s/\$\$NGINX_USER/$USER/g $NGINX_CONF_DIR/nginx.conf.tpl > $NGINX_CONF_DIR/nginx.conf
sed  -i s/\$\$ADMIN_KEY/$1/g $NGINX_CONF_DIR/nginx.conf

echo "Generating random session validation key"
SESSKEY=`< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c10`
sed  -i s/\$\$SESSKEY/$SESSKEY/g $NGINX_CONF_DIR/nginx.conf 
sed  s/\$\$SESSKEY/$SESSKEY/g $TORNADO_CONF_DIR/tornado.conf.tpl > $TORNADO_CONF_DIR/tornado.conf

if test $OPT_INSTALL -eq 1; then
    sed  -i s/\$\$GAUTH/True/g $TORNADO_CONF_DIR/tornado.conf
else
    sed  -i s/\$\$GAUTH/False/g $TORNADO_CONF_DIR/tornado.conf
fi
sed  -i s/\$\$ADMIN_USER/$ADMIN_USER/g $TORNADO_CONF_DIR/tornado.conf
sed  -i s/\$\$NUM_LOCALMAX/$NUM_LOCALMAX/g $TORNADO_CONF_DIR/tornado.conf
sed  -i s/\$\$EXPIRE/$EXPIRE/g $TORNADO_CONF_DIR/tornado.conf
sed  -i s,\$\$DOCKER_IMAGE,$DOCKER_IMAGE,g $TORNADO_CONF_DIR/tornado.conf
sed  -i s,\$\$CLIENT_SECRET,$CLIENT_SECRET,g $TORNADO_CONF_DIR/tornado.conf
sed  -i s,\$\$CLIENT_ID,$CLIENT_ID,g $TORNADO_CONF_DIR/tornado.conf


echo
echo "DONE!"

 
 
