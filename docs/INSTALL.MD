# Installation

JuliaBox is developed and tested on Ubuntu 14.04. But it should be easy to adapt to any Linux environment supporting Docker.

## Installation overview
Installing JuliaBox on a single machine consists of five principal steps, the specifics of which vary depending upon the desired configuration. The following is a general overview of the process, and the key scripts and files involved. It may be useful to consult the included [architecture document](Architecture.md) to gain a high-level overview of JuliaBox before reading these instructions.

1. System preparation.

	Preparation is performed using the `sys_install.sh` script included with the JuliaBox installation. After modification to specify the desired Docker configuration, the script performs the following tasks:
	- installation of requisite system tools & libraries,
	- installation of Docker, addition of current user to Docker group,
	- installation of requisite Python libraries, and,
	- configuration and launch of Docker.

	Finally, the necessary work folders to store data & configuration items must be created.
	
2. JuliaBox configuration.

	The `jbox.user` JuliaBox configuration file is created according to templates provided later in this document. This file sets:
	- limits on the maximum number of active containers, and disks,
	- details of administrators, and,
	- the plugins to be used for this deployment.

	The `jbox_configure.sh` script is executed to configure the JuliaBox installation secret (used as part of encryption key for signing and encrypting session data), and to move the server configuration templates to the work directories (from where they will be mounted by the Docker containers).
	
	On multiuser installations, if it is required to impose limits on available disk space, the `mount_fs.sh` script is executed to configure user home directories. The location, size and number of directories is specified to the script which:
	
	- makes subdirectories to store disk images and form mount points,
	- creates and formats blank disk images in each subdirectory,
	- changes ownership of the disk images to the current user, and,
	- creates loopback devices and mounts the images.

3. *JuliaBox* Docker image creation.

	The `img_create.sh` script is used to build the Docker images which serve users with their own instance of a IJulia notebook, shell, console, and file management facilities. The script performs the following actions:
	- builds the JuliaBox Docker image as specified in `JuliaBox/container/interactive/Dockerfile` and `JuliaBox/container/api/Dockerfile`,
	- executes `mk_user_home.sh` to launch the new JuliaBox container (with a temporary home directory) inside of which it:
		- runs `setup_julia.sh` to add packages as specified in the script,
		- runs `mkjimg.jl` to create a julia system image, and configure IJulia as required,
	- removes configuration files from the temporary home directory,
	- archives the packages and temporary home directory to the work directory, for deployment when a new user logs in.

	The Dockerfiles specifies a base Julia image upon which the JuliaBox image is created. To acquire the base Julia image, you may either pull an existing image from DockerHub, or, build an image from a Dockerfile. Suitable Dockerfiles, configuration scripts, and instructions are hosted [here](https://github.com/tanmaykm/JuliaDockerImages).
	
	There are two ways in which default packages can be included in a deployment,
	
	- by building a custom base Julia image with the desired packages, or, 
	- by modifying `setup_julia.sh` to add the desired packages during creation of the JuliaBox image.

	If choosing the latter option, ensure that any libraries required by your packages are included in the base Julia image.
	
	NOTE: The JuliaBox Dockerfile also automatically downloads and installs a nightly version of Julia into the container (apart from the latest stable version). Packages can also be installed for this version by modifying the `setup_julia.sh` script.

4. *JuliaBox services* Docker image creation.

	JuliaBox service Docker images are also built and tagged by the `img_create.sh` script. Four images, the role of each being detailed in the [architecture document](Architecture.md), are built:
	
	- webserver, the 'router',
	- enginebase, upon which are based:
		- enginedaemon, the 'container manager', and,
		- engineinteractive, the 'interactive session manager'.
		- engineapi, the 'REST API manager'.
	
5. JuliaBox database preperation.

	The JuliaBox database is initialised using the provided `create_tables_*` script, which creates the required tables in the database system chosen for use.
	
JuliaBox is now ready to be launched using the scripts provided in the distribution.	
## Single-machine setup

Before commencing installation:

1.	 If `git` is not yet installed:
	- `sudo apt-get install git`.
2.	Clone JuliaBox sources:
	- `git clone https://github.com/JuliaLang/JuliaBox.git`.

Now continue according to your desired configuration.

### Single-user, zero-authentication

The following procedure will configure a system without authentication, designed to support a single user (for JuliaBox development or personal deployment).

1. System preperation.
	- Install libraries and tools, configure and launch Docker:
    	- Modify `JuliaBox/scripts/install/sys_install.sh` and set `DOCKER_FS` to `AUFS` instead of `DEVICEMAPPER`. This will avoid certain unnecessary configurations required only in certain production environments.
    	- Run `JuliaBox/scripts/install/sys_install.sh`.
	- Create work folders:
		- Execute `sudo mkdir -p /jboxengine/conf /jboxengine/data/db /jboxengine/data/disks/host`.
		- Take ownership `sudo chown -R $USER: /jboxengine`.


2. JuliaBox configuration.
    - Create a configuration file `/jboxengine/conf/jbox.user` as: <pre>
    {
        "numdisksmax": 3,
        "admin_users": ['admin@local.org'],
        "websocket_protocol": "ws",
    	"interactive": {
        	"numlocalmax": 2
        },
        "mnt_location" : "/jboxengine/data/disks/host",
        "backup_location" : None,
        "plugins": [
            "juliabox.plugins.compute_singlenode",
            "juliabox.plugins.vol_hostdisk",
            "juliabox.plugins.vol_defpkg",
            "juliabox.plugins.auth_zero",
            "juliabox.plugins.db_sqlite3"
        ]
    }
    </pre>
    - Generate JuliaBox configuration files:
		- Run `JuliaBox/scripts/install/jbox_configure.sh`.

3. *JuliaBox* Docker image creation.
	
	- Acquire a base Julia image. This can be achieved by pulling an existing image, or building from a specified Dockerfile.

		- To pull an image:
			- [Review available images](https://github.com/tanmaykm/JuliaDockerImages)
			- Pull selected image, e.g., `sudo docker pull julialang/julia:v0.3.11`
			
		- To build an image:
			- Run `docker pull ubuntu:14.04`.
			- Clone template Dockerfiles: `git clone https://github.com/tanmaykm/JuliaDockerImages.git`.
			- Follow instructions in repository to build and tag images.
	
	- Build JuliaBox image on top of selected base image:
		- Modify `FROM` in `JuliaBox/container/interactive/Dockerfile` and `JuliaBox/container/api/Dockerfile` to point to the correct base image.
		- Modify `DEFAULT_PACKAGES` in `JuliaBox/container/interactive/setup_julia.sh` to add any desired packages not included in your base image.
		- Run `JuliaBox/scripts/install/img_create.sh cont build`
		- Run `JuliaBox/scripts/install/img_create.sh home /jboxengine/data`
	
4. *JuliaBox services* Docker image creation.
	- Run `JuliaBox/scripts/install/img_create.sh jbox`

5. JuliaBox database preperation
	- Run `JuliaBox/scripts/install/create_tables_sqlite.py /jboxengine/data/db/juliabox.db`

6. Launch JuliaBox:
    - To start: `JuliaBox/scripts/run/start.sh`
    - To stop: `JuliaBox/scripts/run/stop.sh`

### Multi-user with Google OAuth authentication

1. If you wish to control CPU and RAM usage in containers:
    - Follow the instructions under section "Adjust memory and swap accounting" from <https://docs.docker.com/installation/ubuntulinux/>

2. JuliaBox uses loopback devices to provision user home folders. Most installations are configured for 8 loop devices by default, some of which may already be used by other services. Increase it to slightly more than the number of sessions you wish to support:
    - Add "max_loop=64" to GRUB_CMDLINE_LINUX in file "/etc/default/grub". Replace 64 with an appropriate number.
    - Run `sudo update-grub`.
    - Reboot.
    
3. Sign-up for using [Google Identity](https://developers.google.com/identity/), get the OAuth key and secret to use, and enable the JuliaBox authorisation redirect.
	- In the [Google Developers Console](https://console.developers.google.com) navigate to to the 'Credentials' panel within 'APIs & Auth'.
	- Add a new credential, selecting 'OAuth 2.0 client ID', choose the 'Web application' credential type.
	- Under 'Authorized redirect URIs' enter: `FQDN/jboxauth/google/`, replacing `FQDN` with the correct fully qualified domain name of your server.
	- Note the 'Client ID' and 'Client secret', and save your changes.

4. Complete setup as per single user, zero authentication, <b>replacing step two with</b>:

  - Create a configuration file `/jboxengine/conf/jbox.user` as: <pre>
    {
        "numdisksmax" : 30, # max disks (more than sessions to allow for transitions)
        "admin_users" : ['admin@gmail.com'],  # administrator email id
        "websocket_protocol" : "ws",
    	"interactive": {
        	"numlocalmax": 20  # max concurrent users to support
        },
        "plugins": [
            "juliabox.plugins.compute_singlenode",
            "juliabox.plugins.vol_loopback",
            "juliabox.plugins.vol_defpkg",
            "juliabox.plugins.auth_google",
            "juliabox.plugins.db_sqlite3"
        ],
        "google_oauth": {
            "key": "replace with google oauth key",
            "secret": "replace with google oauth secret"
        },
    }    </pre>
    - Generate JuliaBox configuration files:
		- Run `JuliaBox/scripts/install/jbox_configure.sh`.
	- Create disk images, loopback devices, and mount:
		- Run `sudo JuliaBox/scripts/install/mount_fs.sh /jboxengine/data 30 500 ${USER}`
    - If starting JuliaBox after a system reboot, re-mount the loopback devices by running `mount_fs.sh` as specified in the configuration step above.

## AWS Cluster Setup

TODO
