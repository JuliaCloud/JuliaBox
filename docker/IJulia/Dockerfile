# Docker file for JuliaBox
# Version:12

FROM tanmaykm/juliaboxjulia:julia_v0.3_5

MAINTAINER Tanmay Mohapatra

# Install additional packages required for Julia packages
RUN apt-get install -y \
		hdf5-tools \
		python-sympy \
		glpk-utils \
		libnlopt0 \
		gfortran \
		&& apt-get clean

# add juser
RUN groupadd juser \
    && useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser \
    && echo "export HOME=/home/juser" >> /home/juser/.bashrc

USER juser
ENV HOME /home/juser
WORKDIR /home/juser

# 4200: http port for console
# 8000: http port for tornado
# 8998: ipython port for julia
EXPOSE  4200 8000 8998

ENTRYPOINT /usr/bin/supervisord -n -c /home/juser/.juliabox/supervisord.conf -l /home/juser/.juliabox/supervisord.log -j /home/juser/.juliabox/supervisord.pid -q /home/juser/.juliabox
