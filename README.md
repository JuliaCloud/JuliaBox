## JDock - Docker'ed IJulia containers

### What works

- Runs each IJulia session in its own sandboxed container
- A bash session is aslo started in the container - can be used to run the Julia console REPL
- File upload facility into a session's container
- Basic admin screen to delete old/inactive sessions

### Pending
- Resource limiting containers (cpu / disk)
- Upload .ipynb notebooks for URLs into the container
- Security improvements
- More complete Admin interface
- Prettier UI


### Installing

- The setup script has been tested to work on a fresh Ubuntu 13.04 AMI - viz, ami-ef277b86, but should work on any 13.04 system
- If on EC2, launch an instance from ami-ef277b86 . Make sure you open up ports 22 (ssh) and 80 (http) in your security group 
- On a 13.04 system, make sure your id has `sudo` permissions
- Run the following :

```
sudo apt-get install git

git clone https://github.com/amitmurthy/JDock.git

cd JDock
```

- Run `./setup.sh <admin_key>` 
- `admin_key` above is the session name for an "administration" session. Select something non-guessable.
- Go get a coffee
- NOTE : If you are just updating JDock and do not wish to reinstall packages on your host, do


```
git pull

./setup.sh <admin_key> y

./reload.sh
```

- This will just apply any changes to the LUA scripts and nginx config files. Any changes to your nginx config file will be overwritten.


### Powering up

- `cd <path to JDock>; ./start.sh`
- point your browser to `http://<your_host_address>/`
- `stop.sh` stops nginx, while `reload.sh` gets nginx to reload configuration and lua scripts 




### Notes

- On EC2, the containers are created on the ephemeral volume. They do not persist across a system start/stop
- NGINX and embedded Lua (from http://openresty.org/) has been used to build the web interface
- Not recommended to host on the public internet just yet. 
- Security is mostly a TODO at this time.
- Docker itself is undergoing changes in its API. Since we pull in the latest docker, changes in the docker API may break JDock at any time.
- To get the latest Julia build onto the docker image, you have have to build it with the `-no-cache` option. 
- For example, ./setup.sh executes `sudo docker build -t ijulia docker/IJulia/`. 
- To update docker image `ijulia` with the latest Julia version run `sudo docker build -no-cache -t ijulia docker/IJulia/`
  
## ACKNOWLEDGEMENTS 

- Code examples from the below projects/websites have been used
- Docker - http://www.docker.io/
- OpenResty - http://openresty.org/
- Lua Resty HTTP Client - https://github.com/bakins/lua-resty-http-simple
