# Docker file for JuliaBox Webserver
# Version:1

# Install at /jboxweb
# Place configurations at /jboxweb/conf
# Place static contents at /jboxweb/www
# Place certificates at /jboxweb/certs
# Mount log folder at /jboxweb/logs

FROM ubuntu:14.04

MAINTAINER Tanmay Mohapatra

RUN apt-get update \
    && apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o DPkg::Options::="--force-confold" \
    && apt-get install -y \
    build-essential \
    libreadline-dev \
    libncurses-dev \
    libpcre3-dev \
    libssl-dev \
    netcat \
    git \
    wget \
    lua-socket \
    && apt-get clean

# Create juser which will run the webserver
RUN groupadd juser \
    && useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser \
    && echo "export HOME=/home/juser" >> /home/juser/.bashrc

# Install openresty and add a lua http client script
RUN mkdir -p resty \
    && export NGINX_VER=1.7.10.2 \
    && export NGINX_INSTALL_DIR=/jboxweb/openresty \
    && wget -P resty http://openresty.org/download/ngx_openresty-${NGINX_VER}.tar.gz \
    && cd resty \
    && tar -xvzf ngx_openresty-${NGINX_VER}.tar.gz \
    && cd ngx_openresty-${NGINX_VER} \
    && ./configure --prefix=${NGINX_INSTALL_DIR} \
    && make install \
    && cd ../.. \
    && rm -Rf resty \
    && mkdir -p ${NGINX_INSTALL_DIR}/lualib/resty \
    && wget -P ${NGINX_INSTALL_DIR}/lualib/resty/ https://raw.githubusercontent.com/tanmaykm/lua-resty-http/master/lib/resty/http.lua \
    && wget -P ${NGINX_INSTALL_DIR}/lualib/resty/ https://raw.githubusercontent.com/tanmaykm/lua-resty-http/master/lib/resty/http_headers.lua

# Export volume for logs
RUN mkdir /jboxweb/logs
VOLUME /jboxweb/logs

# Expose the HTTP ports.
# For proxying to work efficiently, it may be best to run the container on host network stack
EXPOSE 80 443

# Add static files, configuration, scripts and certificates
ADD certs /jboxweb/certs
ADD conf /jboxweb/conf
ADD www /jboxweb/www
ADD scripts/router.lua /jboxweb/openresty/lualib/juliabox/

RUN ln -fs /usr/share/lua /usr/local/share/lua \
    && ln -fs /usr/lib/x86_64-linux-gnu/lua /usr/local/lib/lua \
    && cp /jboxweb/conf/logrotate.conf /etc/logrotate.d/jboxweb_logrotate.conf

# Run nginx in foreground (daemon set to off in configuration)
ENTRYPOINT ["/jboxweb/openresty/nginx/sbin/nginx", "-p", "/jboxweb"]
