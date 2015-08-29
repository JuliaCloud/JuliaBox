# Docker file for JuliaBox
# Version:34

FROM julialang/juliaboxpkgdist:v0.3.11
# Switching the base to the bare julia image helps during JuliaBox development by reducing image size
# FROM julialang/julia:v0.3.11

MAINTAINER Tanmay Mohapatra

RUN ln -fs /opt/julia/bin/julia /usr/bin/julia
RUN git clone https://github.com/tanmaykm/shellinabox_fork.git; cd shellinabox_fork; ./configure; make install; cd ..; rm -rf shellinabox_fork

# add juser
# create group and user with specific ids if required on systems where the user running juliabox is not the first user
RUN groupadd juser \
    && useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser \
    && echo "export HOME=/home/juser" >> /home/juser/.bashrc

# add Julia nightly build
RUN mkdir -p /opt/julia_0.4.0 && \
    curl -s -L https://status.julialang.org/download/linux-x86_64 | tar -C /opt/julia_0.4.0 -x -z --strip-components=1 -f -
RUN ln -fs /opt/julia_0.4.0 /opt/julia_nightly

# JuliaBox package bundle shall be mounted at /opt/julia_packages.
# They are added to LOAD_PATH through respective juliarc.jl scripts.
RUN mkdir /opt/julia_packages
RUN echo 'push!(LOAD_PATH, "/opt/julia_packages/.julia/v0.4/")' >> /opt/julia_0.4.0/etc/julia/juliarc.jl
RUN echo 'push!(LOAD_PATH, "/opt/julia_packages/.julia/v0.3/")' >> /opt/julia_0.3.11/etc/julia/juliarc.jl

# Data volumes shall be mounted at /mnt/data
RUN mkdir /mnt/data

USER juser
ENV HOME /home/juser
ENV PATH /usr/local/texlive/2014/bin/x86_64-linux:/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin:/opt/julia/bin
WORKDIR /home/juser

# 4200: http port for console
# 8000: http port for tornado
# 8998: ipython port for julia
# 8050-8052: user specified applications
EXPOSE  4200 8000 8998 8050 8051 8052

ENTRYPOINT ["/usr/bin/supervisord", "-n", "-c", "/home/juser/.juliabox/supervisord.conf", "-l", "/home/juser/.juliabox/supervisord.log", "-j", "/home/juser/.juliabox/supervisord.pid", "-q", "/home/juser/.juliabox"]
