
# Docker file to have a complete Julia installation
# Julia has some issues installing on the 12.04 image, hence using 13.04

FROM saltstack/ubuntu-13.04-minimal

MAINTAINER Amit Murthy

RUN apt-get -y install software-properties-common
RUN add-apt-repository -y ppa:staticfloat/julianightlies
RUN add-apt-repository -y ppa:staticfloat/julia-deps

RUN apt-get -y update

RUN apt-get -y install julia
RUN apt-get -y install build-essential libreadline-dev libncurses-dev libpcre3-dev libssl-dev python-dev libgnutls28 shellinabox wget

RUN apt-get -y install python-setuptools
RUN easy_install ipython[all]

RUN mkdir -p /build/resty
RUN wget -P /build/resty/ http://openresty.org/download/ngx_openresty-1.4.3.3.tar.gz 
RUN bash -c "cd /build/resty; tar -xvzf ngx_openresty-1.4.3.3.tar.gz; cd ngx_openresty-1.4.3.3; ./configure ; make; make install"
RUN rm -Rf /build/resty/ngx_openresty-1.4.3.3*

RUN groupadd juser
RUN useradd -m -d /home/juser -s /bin/bash -g juser juser
RUN echo "export HOME=/home/juser" >> /home/juser/.bashrc
#RUN echo "juser ALL=NOPASSWD: ALL" >> /etc/sudoers
USER juser
ENV HOME /home/juser
WORKDIR /home/juser

RUN ipython profile create julia
#RUN apt-get -y install libzmq-dev
RUN julia -e 'Pkg.init(); Pkg.add("IJulia"); Pkg.add("PyPlot"); Pkg.add("Gadfly");'

RUN echo "c.NotebookApp.open_browser = False" >> /home/juser/.ipython/profile_julia/ipython_notebook_config.py
RUN echo "c.NotebookApp.ip = \"*\"" >> /home/juser/.ipython/profile_julia/ipython_notebook_config.py

RUN mkdir -p /home/juser/resty/logs /home/juser/resty/conf /home/juser/resty/lua /home/juser/resty/www 

ADD nginx.conf /home/juser/resty/conf/
ADD mime.types /home/juser/resty/conf/
ADD upload.lua /home/juser/resty/lua/
ADD contutils.lua /home/juser/resty/lua/
ADD ipnbupl.tpl /home/juser/resty/www/

# ipython port for julia
EXPOSE  8998

# ipython port for nginx
EXPOSE  8000

ENTRYPOINT /usr/local/openresty/nginx/sbin/nginx -p /home/juser/resty && shellinaboxd -b -t -s /:juser:juser:/home/juser:/bin/bash && ipython notebook --profile julia


