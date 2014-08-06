
# Docker file to have a complete Julia installation
# Julia has some issues installing on the 12.04 image, hence using 13.04

FROM saltstack/ubuntu-13.10-minimal

MAINTAINER Amit Murthy

RUN apt-get -y install software-properties-common
RUN add-apt-repository -y ppa:staticfloat/julianightlies
RUN add-apt-repository -y ppa:staticfloat/julia-deps

RUN apt-get -y update

RUN apt-get -y install julia build-essential libreadline-dev libncurses-dev libpcre3-dev libssl-dev python-dev libgnutls28 shellinabox wget file supervisor
RUN apt-get -y install python-setuptools python-numpy python-scipy python-matplotlib python-git

RUN easy_install ipython[all]

RUN groupadd juser
RUN useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser
#RUN usermod -a -G staff juser
RUN echo "export HOME=/home/juser" >> /home/juser/.bashrc
#RUN echo "juser ALL=NOPASSWD: ALL" >> /etc/sudoers
USER juser
ENV HOME /home/juser
WORKDIR /home/juser

RUN ipython profile create julia
#RUN apt-get -y install libzmq-dev
RUN julia -e 'Pkg.init(); Pkg.add("IJulia"); Pkg.add("PyPlot"); Pkg.add("Gadfly"); Pkg.add("DataFrames"); Pkg.add("DataStructures"); Pkg.add("HDF5"); Pkg.add("Iterators"); Pkg.add("MCMC"); Pkg.add("NumericExtensions"); Pkg.add("Optim"); Pkg.add("JuMP");'

RUN echo "c.NotebookApp.open_browser = False" >> /home/juser/.ipython/profile_julia/ipython_notebook_config.py
RUN echo "c.NotebookApp.ip = \"*\"" >> /home/juser/.ipython/profile_julia/ipython_notebook_config.py

RUN mkdir -p /home/juser/.juliabox /home/juser/.juliabox/tornado

ADD tornado /home/juser/.juliabox/tornado/
ADD juliabox.sh /home/juser/.juliabox/
ADD supervisord.conf /home/juser/.juliabox/

# 4200: http port for shellinabox
# 8000: http port for tornado
# 8998: ipython port for julia
EXPOSE  4200 8000 8998

VOLUME ["/juliabox"]
ENTRYPOINT /usr/bin/supervisord -n -c /home/juser/.juliabox/supervisord.conf -l /home/juser/.juliabox/supervisord.log -j /home/juser/.juliabox/supervisord.pid -q /home/juser/.juliabox

