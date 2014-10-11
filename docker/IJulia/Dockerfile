# Docker file for JuliaBox
# Version:15

FROM tanmaykm/jboxjulia:v0.3.2_7

MAINTAINER Tanmay Mohapatra

# Install additional packages required for Julia packages
RUN apt-get update \
    && apt-get install -y \
    hdf5-tools \
    python-sympy \
    glpk-utils \
    libnlopt0 \
    gfortran \
    imagemagick \
    inkscape \
    gettext \
    && apt-get clean

# Sundials
RUN apt-get install -y \
    libsundials-cvode1 \
    libsundials-cvodes2 \
    libsundials-ida2 \
    libsundials-idas0 \
    libsundials-kinsol1 \
    libsundials-nvecserial0 \
    libsundials-serial \
    libsundials-serial-dev \
    && apt-get clean

# NLopt
RUN apt-get install -y \
    libnlopt-dev \
    && apt-get clean

# Ipopt
RUN mkdir ipopt; cd ipopt; wget  http://www.coin-or.org/download/source/Ipopt/Ipopt-3.11.7.tgz; \
    tar -xzf Ipopt-3.11.7.tgz; cd Ipopt-3.11.7; \
    cd ThirdParty/Blas; ./get.Blas; ./configure --prefix=/usr/local --disable-shared --with-pic; make install; cd ../..; \
    cd ThirdParty/Lapack; ./get.Lapack; ./configure --prefix=/usr/local --disable-shared --with-pic; make install; cd ../..; \
    cd ThirdParty/Mumps; ./get.Mumps; cd ../..; \
    ./configure --prefix=/usr/local --enable-dependency-linking --with-blas=/usr/local/lib/libcoinblas.a --with-lapack=/usr/local/lib/libcoinlapack.a; \
    make install; \
    echo "/usr/local/lib" > /etc/ld.so.conf.d/ipopt.conf; ldconfig; \
    cd ../..; \
    rm -rf ipopt

# Cbc
RUN mkdir cbc; cd cbc; wget http://www.coin-or.org/download/source/Cbc/Cbc-2.8.12.tgz; \
    tar -xzf Cbc-2.8.12.tgz; cd Cbc-2.8.12; \
    ./configure --prefix=/usr/local --enable-dependency-linking --without-blas --without-lapack --enable-cbc-parallel; \
    make install; \
    echo "/usr/local/lib" > /etc/ld.so.conf.d/cbc.conf; ldconfig; \
    cd ../..; \
    rm -rf cbc

# MPI
RUN apt-get install -y \
    openmpi-bin \
    libopenmpi-dev \
    && apt-get clean

# add juser
# create group and user with specific ids if required on systems where the user running juliabox is not the first user
RUN groupadd juser \
    && useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser \
    && echo "export HOME=/home/juser" >> /home/juser/.bashrc

USER juser
ENV HOME /home/juser
ENV PATH /usr/local/texlive/2014/bin/x86_64-linux:/usr/local/bin:/usr/bin:/bin:/usr/games
WORKDIR /home/juser

# 4200: http port for console
# 8000: http port for tornado
# 8998: ipython port for julia
EXPOSE  4200 8000 8998

ENTRYPOINT /usr/bin/supervisord -n -c /home/juser/.juliabox/supervisord.conf -l /home/juser/.juliabox/supervisord.log -j /home/juser/.juliabox/supervisord.pid -q /home/juser/.juliabox
