# Docker file for JuliaBox
# Version:3

FROM stackbrew/ubuntu:saucy

MAINTAINER Amit Murthy

# Enable the necessary sources and upgrade to latest
RUN echo "deb http://archive.ubuntu.com/ubuntu saucy main universe multiverse restricted" > /etc/apt/sources.list && \
  apt-get update && \
  apt-get upgrade -y -o DPkg::Options::=--force-confold

# Add the Julia PPA
RUN apt-get install -y -o DPkg::Options::=--force-confold apt-utils python-software-properties software-properties-common && \
  apt-add-repository -y ppa:staticfloat/julianightlies && \
  add-apt-repository -y ppa:staticfloat/julia-deps && \
  apt-get clean && \
  apt-get update

# Install core packages
RUN apt-get install -y \
  build-essential \
  wget \
  file \
  vim \
  libreadline-dev \
  libncurses-dev \
  libpcre3-dev \
  libgnutls28 \
  python \
  python-yaml \
  python-m2crypto \
  python-crypto \
  msgpack-python \
  python-dev \
  python-setuptools \
  supervisor \
  julia \
  && apt-get clean


# Install additional packages
RUN apt-get install -y \
  python-zmq \
  python-jinja2 \
  python-requests \
  python-numpy \
  python-scipy \
  python-matplotlib \
  python-isodate \
  python-git \
  python-pip \
  && apt-get clean


# Install additional packages required for Julia packages
RUN apt-get install -y \
  hdf5-tools \
  python-sympy \
  && apt-get clean
  
RUN pip install --upgrade PyDrive google-api-python-client ipython[all]

RUN git clone https://github.com/tanmaykm/shellinabox_fork.git; cd shellinabox_fork; ./configure; make install; cd ..; rm -rf shellinabox_fork

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
RUN julia -e 'Pkg.init(); Pkg.add("IJulia"); Pkg.add("PyPlot"); Pkg.add("Gadfly"); Pkg.add("DataFrames"); Pkg.add("DataStructures"); Pkg.add("HDF5"); Pkg.add("Iterators"); Pkg.add("MCMC"); Pkg.add("NumericExtensions"); Pkg.add("Optim"); Pkg.add("JuMP"); Pkg.add("SymPy");'

RUN echo "c.NotebookApp.open_browser = False" >> /home/juser/.ipython/profile_julia/ipython_notebook_config.py
RUN echo "c.NotebookApp.ip = \"*\"" >> /home/juser/.ipython/profile_julia/ipython_notebook_config.py
COPY custom.css /home/juser/.ipython/profile_julia/static/custom/custom.css

RUN mkdir -p /home/juser/.juliabox /home/juser/.juliabox/tornado

ADD tornado /home/juser/.juliabox/tornado/
ADD juliabox.sh /home/juser/.juliabox/
ADD supervisord.conf /home/juser/.juliabox/

# 4200: http port for console
# 8000: http port for tornado
# 8998: ipython port for julia
EXPOSE  4200 8000 8998

VOLUME ["/juliabox"]
ENTRYPOINT /usr/bin/supervisord -n -c /home/juser/.juliabox/supervisord.conf -l /home/juser/.juliabox/supervisord.log -j /home/juser/.juliabox/supervisord.pid -q /home/juser/.juliabox

