# Docker file for JuliaBox APIs
# Version:34

FROM julialang/juliaboxpkgdist:v0.3.11

MAINTAINER Tanmay Mohapatra

RUN ln -fs /opt/julia/bin/julia /usr/bin/julia

# add juser
# create group and user with specific ids if required on systems where the user running juliabox is not the first user
RUN groupadd juser \
    && useradd -m -d /home/juser -s /bin/bash -g juser -G staff juser \
    && echo "export HOME=/home/juser" >> /home/juser/.bashrc

# add Julia nightly build
RUN mkdir -p /opt/julia_0.4.0 && \
    curl -s -L https://status.julialang.org/download/linux-x86_64 | tar -C /opt/julia_0.4.0 -x -z --strip-components=1 -f -
RUN ln -fs /opt/julia_0.4.0 /opt/julia_nightly

USER juser
ENV HOME /home/juser
ENV PATH /usr/local/texlive/2014/bin/x86_64-linux:/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin:/opt/julia/bin
WORKDIR /home/juser

RUN /opt/julia_0.4.0/bin/julia  -e "try; Pkg.installed(\"JuliaWebAPI\"); catch; Pkg.clone(\"https://github.com/tanmaykm/JuliaWebAPI.jl\"); end"
RUN /opt/julia_0.3.11/bin/julia -e "try; Pkg.installed(\"JuliaWebAPI\"); catch; Pkg.clone(\"https://github.com/tanmaykm/JuliaWebAPI.jl\"); end"

ENTRYPOINT ["julia", "-e", "using JuliaWebAPI; using Compat; process();"]
