## JDock - Docker'ed IJulia containers

### What works

- Runs each IJulia session in its own sandboxed container
- A bash session is aslo started in the container - can be used to run the Julia console REPL
- File upload facility into a session's container
- Basic admin screen to delete old/inactive sessions
- Support Google auth

### Pending
- Google drive integration
- Auto cleanup of sessions based on inactivity
- Resource limiting containers (cpu / disk)
- Upload .ipynb notebooks by URLs directly into the container
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

setup.sh has the following options:

```
Usage: ./setup.sh  -u <admin_username> optional_args
 -u  <username> : Mandatory admin username. If -g option is used, this must be the complete Google email-id
 -d             : Only recreate docker image - do not install/update other software
 -g             : Use Google Openid for user authentication 
 -n  <num>      : Maximum number of active containers. Deafult 10.
 -t  <seconds>  : Auto delete containers older than specified seconds. 0 means never expire. Default 0.
```


- `admin_username` above is the session name for an "administration" session. If not using Google auth, select something non-guessable.
- Go get a coffee, this while take a while
- NOTE : If you are just updating JDock and do not wish to reinstall packages on your host, use the `-d` option


```
git pull

./setup.sh -u <admin_username> -d 

./reload.sh
```

- This will just apply any changes to the scripts and nginx config files. Any changes to your nginx config file will be overwritten.

### Additional configuration
Create a file called tornado.user in the installation's root directory. It should contain a JSON dictionary of the form

```
{
  "protected_sessions" : ['amitm'],
  "numlocalmax" : 3,
  "admin_users" : [],
  "dummy" : "dummy"
}
```

where 

`protected_sessions` are those sessions which will not be timed out and auto-cleaned up
`numlocalmax` is the maximum number of concurrent sessions to be allowed. Default is 10.
`admin_users` is a list of users that have access to the admin tab. Empty means everyone has access.



### Powering up

- `cd <path to JDock>; ./start.sh`
- point your browser to `http://<your_host_address>/`
- `stop.sh` stops nginx and tornado, while `reload.sh` restarts the servers




### Notes

- On EC2, the containers are created on the ephemeral volume. They do not persist across a system start/stop
- NGINX and embedded Lua (from http://openresty.org/) and tornado have been used to build the web interface
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
