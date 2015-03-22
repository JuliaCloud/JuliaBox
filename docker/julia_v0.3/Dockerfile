# Base Dockerfile with Julia 0.3 release
# Version:16

FROM tanmaykm/jboxcore:11

MAINTAINER Tanmay Mohapatra

# Add the Julia PPA
RUN apt-get install -y -o Dpkg::Options::="--force-confdef" -o DPkg::Options::="--force-confold" apt-utils python-software-properties software-properties-common \
    && apt-add-repository -y ppa:staticfloat/juliareleases \
    && add-apt-repository -y ppa:staticfloat/julia-deps \
    && apt-get update \
    && apt-get install -y julia=0.3.6-depsfix10-trusty \
    && apt-get clean
