# Docker file for JuliaBox
# Version:4

FROM tanmaykm/juliaboxdockerbase:julia_nightly

MAINTAINER Amit Murthy

# Install additional packages required for Julia packages
RUN apt-get install -y \
        hdf5-tools \
        python-sympy \
        && apt-get clean

RUN groupadd juser
RUN useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser
RUN chown juser:juser /home/juser
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
