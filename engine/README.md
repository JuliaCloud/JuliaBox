
JuliaBox Engines implement container management.

It is possible to have different container management strategies for different types of containers.

A base engine provides common functionality. The base engine runs in privileged mode and provides common 
functionalities over a ZMQ based API. Other engines are build on this base, and communicate with the base
over the provided ZMQ interface.


## Building

````
cd JuliaBox/engine
docker build -t juliabox/enginebase -f Dockerfile.base .
docker build -t juliabox/enginedaemon -f Dockerfile.daemon .
docker build -t juliabox/engineinteractive -f Dockerfile.interactive .
````
