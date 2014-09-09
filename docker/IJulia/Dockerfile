# Docker file for JuliaBox
# Version:10

FROM tanmaykm/juliaboxjulia:julia_v0.3_3

MAINTAINER Tanmay Mohapatra

# Install additional packages required for Julia packages
RUN apt-get install -y \
        hdf5-tools \
        python-sympy \
		glpk-utils \
		libnlopt0 \
		gfortran \
		pkg-config \
		pandoc \
        && apt-get clean

RUN mkdir -p /.julia \
	&& chmod 777 /.julia

USER juser
ENV HOME /home/juser
WORKDIR /home/juser

RUN echo "export JULIA_PKGDIR=/.julia" >> /home/juser/.bashrc
RUN ipython profile create julia
RUN export JULIA_PKGDIR=/.julia && julia -e 'Pkg.init(); Pkg.add("IJulia"); Pkg.add("PyPlot"); Pkg.add("Gadfly"); Pkg.add("DataFrames"); Pkg.add("DataStructures"); Pkg.add("HDF5"); Pkg.add("Iterators"); Pkg.add("MCMC"); Pkg.add("NumericExtensions"); Pkg.add("SymPy"); Pkg.add("Interact");'
RUN export JULIA_PKGDIR=/.julia && julia -e 'Pkg.add("Optim"); Pkg.add("JuMP"); Pkg.add("GLPKMathProgInterface"); Pkg.add("Clp");'
RUN export JULIA_PKGDIR=/.julia && julia -e 'Pkg.add("NLopt"); Pkg.add("Ipopt");'

RUN echo "c.NotebookApp.open_browser = False" >> /home/juser/.ipython/profile_julia/ipython_notebook_config.py \
	&& echo "c.NotebookApp.ip = \"*\"" >> /home/juser/.ipython/profile_julia/ipython_notebook_config.py
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
