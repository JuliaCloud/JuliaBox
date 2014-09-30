## JuliaBox - Hosted IJulia Containers

### Features

- Runs each IJulia session in its own sandboxed container.
- A bash session is also started in the container - can be used to run the Julia console REPL.
- File transfer facility into a session's container.
- File synchronization with remote git repositories &amp; Google Drive.
- Basic admin screen to delete old/inactive sessions.
- Login via. Google authentication.
- Auto cleanup of sessions based on inactivity.
- Ability to limit memory and CPU allocated for user sessions.
- [Packages installed](PACKAGES.md)


### Installation

- The setup script has been tested to work on a fresh Ubuntu 14.04 AMI - viz, ami-80778be8, but should work on any 14.04 system
- If on EC2
    - Launch an instance from ami-80778be8.
    - Open up ports 22 (ssh), 80 (http), 443 (https) in the security group for both incoming and outgoing traffic. 
    - Open outgoing UDP port 53 (dns), if machine is configured inside a VPC.
    - Optionally open outgoing port 9418 (git).
- Clone JuliaBox (`sudo apt-get install git; git clone https://github.com/JuliaLang/JuliaBox.git`)
- JuliaBox uses Amazon DynamoDB to store user credentials, S3 to store user data, and Python Boto package to access AWS. Set them up from a script or AWS console:
    - Create a Amazon IAM user named `juliabox` and get the AWS credentials for the user. Grant appropriate permissions to the user.
    - Create a boto configuration file with the above AWS credentials as described here: <http://boto.readthedocs.org/en/latest/boto_config_tut.html>.
    - Create DynamoDB tables for tables used from `db/*.py` sources.
    - Create a S3 bucket named `juliabox-userbackup`.
- Use scripts from [install folder](scripts/README.md) to complete the installation.


### Powering up

- `cd <path to JuliaBox>`
- Optionally create a file named `jbox.user` that contain a subset of parameters from `host/tornado/conf/tornado.conf` that you wish to customize
- Use scripts from [run folder](scripts/README.md) to start and stop the server.
- Start the server with `./scripts/run/start.sh`
- Point your browser to `http://<your_host_address>/`
- Stop the server with `./scripts/run/stop.sh`, and restart it with `./scripts/run/reload.sh`. You may change parameters in `jbox.user` and run `reload.sh` for them to take effect.


### TODO
- Creating/selecting a custom image that has been extended from the base JuliaBox provided image.
- Upload .ipynb notebooks by URLs directly into the container.
- Security improvements.
- More complete Admin interface.
- Prettier UI. Help/tips for users.
- Launching remote docker instances.

