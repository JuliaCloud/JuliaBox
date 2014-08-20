## JuliaBox - Hosted IJulia Containers

### Packages installed

Following packages are installed by default. Additional packages can be installed and existing packages can be upgraded by users as desired.

- 10 required packages:
    - DataFrames
    - DataStructures
    - Gadfly
    - HDF5
    - IJulia
    - Iterators
    - JuMP
    - MCMC
    - NumericExtensions
    - Optim
    - PyPlot
- 29 additional packages:
    - ArrayViews
    - BinDeps
    - Calculus
    - Codecs
    - Color
    - Compose
    - Contour
    - DataArrays
    - Datetime
    - Distance
    - Distributions
    - DualNumbers
    - GZip
    - Graphs
    - Hexagons
    - ImmutableArrays
    - JSON
    - Loess
    - MathProgBase
    - Nettle
    - NumericFuns
    - Options
    - PDMats
    - PyCall
    - REPLCompletions
    - Reexport
    - ReverseDiffSource
    - ReverseDiffSparse
    - SortingAlgorithms
    - StatsBase
    - URIParser
    - ZMQ

### Features

- Runs each IJulia session in its own sandboxed container.
- A bash session is aslo started in the container - can be used to run the Julia console REPL.
- File transfer facility into a session's container.
- File synchronization with remote git repositories &amp; Google Drive.
- Basic admin screen to delete old/inactive sessions.
- Login via. Google authentication.
- Auto cleanup of sessions based on inactivity.
- Ability to limit memory usage for user sessions.


### Installation

- The setup script has been tested to work on a fresh Ubuntu 14.04 AMI - viz, ami-80778be8, but should work on any 14.04 system
- If on EC2
    - Launch an instance from ami-80778be8.
    - Open up ports 22 (ssh), 80 (http), 443 (https) in the security group for both incoming and outgoing traffic. 
    - Open outgoing UDP port 53 (dns), if machine is configured inside a VPC.
    - Optionally open outgoing port 9418 (git).
- On a 14.04 system, make sure your id has `sudo` permissions.
- Run the following:
    - `sudo apt-get install git`
    - `git clone https://github.com/JuliaLang/JuliaBox.git`
    - `cd JuliaBox`
- JuliaBox uses Amazon DynamoDB to store user credentials, S3 to store user data, and Python Boto package to access AWS. To set them up:
    - Log in to Amazon AWS.
    - Create a DynamoDB table named `jbox_users` with hash key attribute `user_id`.
    - Create a S3 bucket named `juliabox_userbackup`.
    - Create a Amazon IAM user named `juliabox` and get the AWS credentials for the user.
    - Grant read and write permissions to `juliabox` user for `jbox_users` DynamoDB table and `juliabox_userbackup` S3 bucket.
    - Create a boto configuration file with the above AWS credentials as described here: <http://boto.readthedocs.org/en/latest/boto_config_tut.html>.
- Run `setup.sh` with appropriate options.
    - `admin_username` above is the session name for an "administration" session. If not using Google auth, select something non-guessable.
    - Go get a coffee, this will take a while


Options available with `setup.sh`:

```
Usage: ./setup.sh -u <admin_username> optional_args
 -u  <username> : Mandatory admin username. If -g option is used, this must be the complete Google email-id
 -g             : Use Google OAuth2 for user authentication. Options -k and -s must be specified.
 -k  <key>      : Google OAuth2 key (client id).
 -s  <secret>   : Google OAuth2 client secret.
 -d             : Only recreate docker image - do not install/update other software
 -n  <num>      : Maximum number of active containers. Deafult 10.
 -t  <seconds>  : Auto delete containers older than specified seconds. 0 means never expire. Default 0.
```


### Powering up

- `cd <path to JuliaBox>; ./start.sh`
- Point your browser to `http://<your_host_address>/`
- `stop.sh` stops nginx and tornado, while `reload.sh` restarts the servers


### Additional configuration
Create a file called jbox.user in the installation's root directory. It should contain a JSON dictionary of the form

```
{
  "protected_sessions" : ['amitm'],
  "numlocalmax" : 3,
  "admin_users" : [],
  "mem_limit" : 1000000000,
  "inactivity_timeout" : 300,
  "expire" : 0,
  "dummy" : "dummy"
}
```

where 

- `protected_sessions` are those sessions which will not be timed out and auto-cleaned up
- `numlocalmax` is the maximum number of concurrent sessions to be allowed. Default is 10 or the number specified while running ./setup.sh .
- `admin_users` is a list of users that have access to the admin tab. Empty means everyone has access.
- `mem_limit` is a maximum memory allowed per docker container (running a local nginx, ijulia, bash as well as the users julia sessions). Default is 1GB.
    - NOTE: To be able to use `mem_limit`, the host kernel must be configured to support the same. 
    - See <http://docs.docker.io/en/latest/installation/kernel/#memory-and-swap-accounting-on-debian-ubuntu> 
- `inactivity_timeout` specifies the time in seconds to wait before clearing an inactive session, for example, when the user closes the browser window . 
    - Default is 300 seconds. `protected_sessions` are not affected.
- `expire` specifes an upper time limit for a user session before it is auto-deleted. 0 means never expire. `protected_sessions` are not affected.


You will need to run `reload.sh` for any changed parameters to take affect.


### Server Maintenance

If you are just updating JuliaBox and do not wish to reinstall packages on your host, use the `-d` option. This will just apply any changes to the scripts and nginx config files. Any changes to your nginx config file will be overwritten.

```
git pull

./setup.sh -u <admin_username> -d 

./reload.sh
```

To get the latest Julia build onto the docker image, you have have to build it with the `-no-cache` option. E.g. `sudo docker build -no-cache ...`.

User containers are backed up and removed from docker after configured inactivity time. They are re-constituted when a user returns and the backed up files are restored into the new container instance. Location where containers are backed up can be configured via parameter `backup_location`.

Unwanted/old images take up unecessary disk space. To clear them run `sudo docker rmi $(sudo docker images | grep "^<none>" | tr -s ' ' | cut -d ' ' -f 3)`.


### TODO
- Limiting disk usage by session.
- Creating/selecting a custom image that has been extended from the base JuliaBox provided image.
- Upload .ipynb notebooks by URLs directly into the container.
- Security improvements.
- More complete Admin interface.
- Prettier UI. Help/tips for users.
- Launching remote docker instances.


### Notes

- On EC2, the containers are created on the ephemeral volume. They do not persist across a system start/stop
- NGINX and embedded Lua (from <http://openresty.org/>) and tornado have been used to build the web interface
- Not recommended to host on the public internet just yet. 
- Security is mostly a TODO at this time.
- Docker itself is undergoing changes in its API. Since we pull in the latest docker, changes in the docker API may break JuliaBox at any time.
  
## Acknowledgements 

Code examples from the below projects/websites have been used:
- Docker - <http://www.docker.io/>
- OpenResty - <http://openresty.org/>
- Lua Resty HTTP Client - <https://github.com/bakins/lua-resty-http-simple>

