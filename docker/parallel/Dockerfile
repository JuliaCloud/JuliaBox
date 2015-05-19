# Docker file for JuliaBox
# Version:30

FROM julialang/juliaboxpkgdist:v0.3.8

MAINTAINER Tanmay Mohapatra

# install Julia 0.4
RUN mkdir -p /opt/julia_0.4.0 && \
    curl -s -L https://status.julialang.org/download/linux-x86_64 | tar -C /opt/julia_0.4.0 -x -z --strip-components=1 -f -

RUN rm /opt/julia
RUN ln -fs /opt/julia_0.4.0 /opt/julia
RUN ln -fs /opt/julia/bin/julia /usr/bin/julia
RUN git clone https://github.com/tanmaykm/shellinabox_fork.git; cd shellinabox_fork; ./configure; make install; cd ..; rm -rf shellinabox_fork

# add juser
# create group and user with specific ids if required on systems where the user running juliabox is not the first user
RUN groupadd juser \
    && useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser \
    && echo "export HOME=/home/juser" >> /home/juser/.bashrc

USER juser
ENV HOME /home/juser
ENV PATH /usr/local/texlive/2014/bin/x86_64-linux:/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin:/opt/julia/bin
WORKDIR /home/juser

# 4200: http port for console
# 8000: http port for tornado
# 8998: ipython port for julia
EXPOSE  4200 8000 8998

ENTRYPOINT /usr/bin/supervisord -n -c /home/juser/.juliabox/supervisord.conf -l /home/juser/.juliabox/supervisord.log -j /home/juser/.juliabox/supervisord.pid -q /home/juser/.juliabox

