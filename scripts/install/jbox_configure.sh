#! /usr/bin/env bash
# Configure JuliaBox components

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JBOX_DIR=`readlink -e ${DIR}/../..`

source ${DIR}/../jboxcommon.sh

DOCKER_IMAGE=juliabox/juliabox
OPT_GOOGLE=0
OPT_INVITE=0
NUM_LOCALMAX=2
NUM_DISKSMAX=2
EXPIRE=0

function usage {
  echo
  echo 'Usage: ./setup.sh -u <admin_username> optional_args'
  echo ' -u  <username> : Mandatory admin username. If -g option is used, this must be the complete Google email-id'
  echo ' -g             : Use Google OAuth2 for user authentication. Options -k and -s must be specified.'
  echo ' -k  <key>      : Google OAuth2 key (client id).'
  echo ' -s  <secret>   : Google OAuth2 client secret.'
  echo ' -n  <num>      : Maximum number of active containers. Default 2.'
  echo ' -v  <num>      : Maximum number of mountable volumes. Default 2.'
  echo ' -t  <seconds>  : Auto delete containers older than specified seconds. 0 means never expire. Default 0.'
  echo ' -i             : Install in an invite only mode.'
  echo
  echo 'Post setup, additional configuration parameters may be set in jbox.user '
  echo 'Please see README.md (https://github.com/JuliaLang/JuliaBox) for more details '
  
  exit 1
}

function gen_sesskey {
    echo "Generating random session validation key"
    SESSKEY=`< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c32`
    echo $SESSKEY > .jbox_session_key
}

function configure_resty_tornado {
    echo "Setting up nginx.conf ..."
    sed  s/\$\$NGINX_USER/$USER/g $NGINX_CONF_DIR/nginx.conf.tpl > $NGINX_CONF_DIR/nginx.conf
    sed  -i s/\$\$ADMIN_KEY/$1/g $NGINX_CONF_DIR/nginx.conf

    sed  -i s/\$\$SESSKEY/$SESSKEY/g $NGINX_CONF_DIR/nginx.conf 
    sed  s/\$\$SESSKEY/$SESSKEY/g $TORNADO_CONF_DIR/tornado.conf.tpl > $TORNADO_CONF_DIR/tornado.conf

    if test $OPT_GOOGLE -eq 1; then
        sed  -i s/\$\$GAUTH/True/g $TORNADO_CONF_DIR/tornado.conf
    else
        sed  -i s/\$\$GAUTH/False/g $TORNADO_CONF_DIR/tornado.conf
    fi
    if test $OPT_INVITE -eq 1; then
        sed  -i s/\$\$INVITE/True/g $TORNADO_CONF_DIR/tornado.conf
    else
        sed  -i s/\$\$INVITE/False/g $TORNADO_CONF_DIR/tornado.conf
    fi

    sed  -i s/\$\$ADMIN_USER/$ADMIN_USER/g $TORNADO_CONF_DIR/tornado.conf
    sed  -i s/\$\$NUM_LOCALMAX/$NUM_LOCALMAX/g $TORNADO_CONF_DIR/tornado.conf
    sed  -i s/\$\$NUM_DISKSMAX/$NUM_DISKSMAX/g $TORNADO_CONF_DIR/tornado.conf
    sed  -i s/\$\$EXPIRE/$EXPIRE/g $TORNADO_CONF_DIR/tornado.conf
    sed  -i s,\$\$DOCKER_IMAGE,$DOCKER_IMAGE,g $TORNADO_CONF_DIR/tornado.conf
    sed  -i s,\$\$CLIENT_SECRET,$CLIENT_SECRET,g $TORNADO_CONF_DIR/tornado.conf
    sed  -i s,\$\$CLIENT_ID,$CLIENT_ID,g $TORNADO_CONF_DIR/tornado.conf
}


while getopts  "u:idgn:v:t:k:s:" FLAG
do
  if test $FLAG == '?'
     then
        usage

  elif test $FLAG == 'u'
     then
        ADMIN_USER=$OPTARG

  elif test $FLAG == 'g'
     then
        OPT_GOOGLE=1

  elif test $FLAG == 'i'
     then
        OPT_INVITE=1

  elif test $FLAG == 'n'
     then
        NUM_LOCALMAX=$OPTARG

  elif test $FLAG == 'v'
     then
        NUM_DISKSMAX=$OPTARG

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


if [ ! -e .jbox_session_key ]
then
    gen_sesskey
fi
SESSKEY=`cat .jbox_session_key`

configure_resty_tornado

echo
echo "DONE!"
 
