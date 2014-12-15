# Base Dockerfile with Julia 0.3 release
# Version:11

FROM tanmaykm/jboxcore:9

MAINTAINER Tanmay Mohapatra

# Add the Julia PPA
RUN apt-get install -y -o Dpkg::Options::="--force-confdef" -o DPkg::Options::="--force-confold" apt-utils python-software-properties software-properties-common \
    && apt-add-repository -y ppa:staticfloat/juliareleases \
    && add-apt-repository -y ppa:staticfloat/julia-deps \
    && apt-get update \
    && apt-get install -y julia=0.3.3~trusty1 \
    && apt-get clean

