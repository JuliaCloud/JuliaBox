# Docker file for JuliaBox APIs
# Version:37

FROM julialang/juliaboxpkgdist:v0.3.11

MAINTAINER Tanmay Mohapatra

RUN ln -fs /opt/julia/bin/julia /usr/bin/julia

# add juser
# create group and user with specific ids if required on systems where the user running juliabox is not the first user
RUN groupadd juser \
    && useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser \
    && echo "export HOME=/home/juser" >> /home/juser/.bashrc

# link Julia v0.3
RUN ln -fs /opt/julia_0.3.11 /opt/julia-0.3.11 && \
    ln -fs /opt/julia-0.3.11 /opt/julia-0.3

# add Julia v0.4 build
RUN mkdir -p /opt/julia-0.4.0 && \
    curl -s -L https://julialang.s3.amazonaws.com/bin/linux/x64/0.4/julia-0.4.0-linux-x86_64.tar.gz | tar -C /opt/julia-0.4.0 -x -z --strip-components=1 -f -
RUN ln -fs /opt/julia-0.4.0 /opt/julia-0.4

# add Julia v0.5 nightly build
RUN mkdir -p /opt/julia-0.5.0-dev && \
    curl -s -L https://status.julialang.org/download/linux-x86_64 | tar -C /opt/julia-0.5.0-dev -x -z --strip-components=1 -f -
RUN ln -fs /opt/julia-0.5.0-dev /opt/julia-0.5

USER juser
ENV HOME /home/juser
ENV PATH /usr/local/texlive/2014/bin/x86_64-linux:/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin:/opt/julia/bin
WORKDIR /home/juser

RUN /opt/julia-0.3/bin/julia  -e "try; Pkg.installed(\"JuliaWebAPI\"); catch; Pkg.clone(\"https://github.com/tanmaykm/JuliaWebAPI.jl\"); end"
RUN /opt/julia-0.4/bin/julia  -e "try; Pkg.installed(\"JuliaWebAPI\"); catch; Pkg.clone(\"https://github.com/tanmaykm/JuliaWebAPI.jl\"); end"
RUN /opt/julia-0.5/bin/julia  -e "try; Pkg.installed(\"JuliaWebAPI\"); catch; Pkg.clone(\"https://github.com/tanmaykm/JuliaWebAPI.jl\"); end"

ENTRYPOINT ["julia", "-e", "using JuliaWebAPI; using Compat; process();"]
