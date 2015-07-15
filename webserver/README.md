
JuliaBox Webserver serves static content and acts as a gateway/router. The webserver can authenticate
access to paths protected with JuliaBox provided authentication. It can route connections across instaces
based on rules built on cookies and URL format.


## Building

````
cd JuliaBox/webserver
docker build -t juliabox/webserver -f Dockerfile .
````
