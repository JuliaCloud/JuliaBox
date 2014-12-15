# Base Ubuntu Docker file for JuliaBox
# Version:9

FROM stackbrew/ubuntu:trusty

MAINTAINER Tanmay Mohapatra

# Enable the necessary sources and upgrade to latest
RUN apt-get update \
    && apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o DPkg::Options::="--force-confold" \
# Install core packages
    && apt-get install -y \
    man-db \
    libc6 \
    libc6-dev \
    build-essential \
    wget \
    curl \
    file \
    vim \
    screen \
    tmux \
    pkg-config \
    pandoc \
    pdf2svg \
    inotify-tools \
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
# Install additional packages
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

ADD texlive.profile /tmp/tl/texlive.profile
RUN cd /tmp/tl; wget http://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz; \
    tar -xzf install-tl-unx.tar.gz; cd install-tl-2014*; \
    ./install-tl --profile=../texlive.profile; cd /; rm -rf /tmp/tl; \
    echo "export PATH=/usr/local/texlive/2014/bin/x86_64-linux:\$PATH" > /etc/profile.d/texlive.sh; \
    echo "export INFOPATH=/usr/local/texlive/2014/texmf-dist/doc/info:\$INFOPATH" >> /etc/profile.d/texlive.sh; \
    echo "export MANPATH=/usr/local/texlive/2014/texmf-dist/doc/man:\$MANPATH" >>  /etc/profile.d/texlive.sh; \
    chmod 755 /etc/profile.d/texlive.sh

#RUN cd /tmp/tl; git clone https://github.com/scottkosty/install-tl-ubuntu.git; \
#    ./install-tl-ubuntu/install-tl-ubuntu --allow-small --profile /tmp/tl/texlive.profile --retry 5; \
#    cd /; rm -rf /tmp/tl; \
#    echo "export PATH=/usr/local/texlive/2014/bin/x86_64-linux:\$PATH" > /etc/profile.d/texlive.sh; \
#    echo "export INFOPATH=/usr/local/texlive/2014/texmf-dist/doc/info:\$INFOPATH" >> /etc/profile.d/texlive.sh; \
#    echo "export MANPATH=/usr/local/texlive/2014/texmf-dist/doc/man:\$MANPATH" >>  /etc/profile.d/texlive.sh; \
#    chmod 755 /etc/profile.d/texlive.sh

RUN pip install --upgrade PyDrive google-api-python-client jsonpointer jsonschema tornado sphinx pygments nose readline mistune

RUN git clone --recursive https://github.com/tanmaykm/ipython.git; cd ipython; git checkout juliabox; python setup.py install; cd ..; rm -rf ipython

RUN git clone https://github.com/tanmaykm/shellinabox_fork.git; cd shellinabox_fork; ./configure; make install; cd ..; rm -rf shellinabox_fork

