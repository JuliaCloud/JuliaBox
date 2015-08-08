## Installation

JuliaBox is developed and tested on Ubuntu 14.04. But it should be easy to adapt to any Linux environment supporting Docker.

### Single Machine Development Setup
1. Get JuliaBox sources:
    - If `git` is not installed yet, run: `sudo apt-get install git`
    - `git clone https://github.com/tanmaykm/JuliaDockerImages.git`
    - `git clone https://github.com/JuliaLang/JuliaBox.git`
2. Install docker and a few more packages required to develop and administer JuliaBox:
    - Modify `JuliaBox/scripts/install/sys_install.sh` and set `DOCKER_FS` to `AUFS` instead of `DEVICEMAPPER`.
        - This will avoid certain unnecessary configurations required only in certain production environments.
    - Run `JuliaBox/scripts/install/sys_install.sh`
3. Create work folders: `mkdir -p /jboxengine/conf /jboxengine/data /jboxengine/data/db`
4. Configure JuliaBox:
    - Create a configuration file `/jboxengine/conf/jbox.user` as: <pre>
    {
        "numlocalmax" : 2,
        "numdisksmax" : 3,
        "admin_users" : ['admin@local.org'],
        "websocket_protocol" : "ws",
        "plugins": [
            "juliabox.plugins.compute_singlenode",
            "juliabox.plugins.vol_loopback",
            "juliabox.plugins.vol_defpkg",
            "juliabox.plugins.auth_zero",
            "juliabox.plugins.db_sqlite3"
        ]
    }
    </pre>
    - Run `JuliaBox/scripts/install/jbox_configure.sh` to generate JuliaBox configuration files.
    - Run `sudo JuliaBox/scripts/install/mount_fs.sh /jboxengine/data 3 500 ${USER}` to create loopback devices for JuliaBox user home volumes.
5. Pull/build docker images:
    - Pull/build base docker images, by following instructions at:
        - Pull the base ubuntu image (only if building). Run: `docker pull ubuntu:14.04`
        - <https://github.com/tanmaykm/JuliaDockerImages/tree/master/base/v0.3>
        - <https://github.com/tanmaykm/JuliaDockerImages/tree/master/pkgdists/juliaboxminimal>
        - <https://github.com/tanmaykm/JuliaDockerImages/tree/master/pkgdists/juliabox>
    - Build JuliaBox images:
        - Julia and default package bundles. Run: `JuliaBox/scripts/install/img_create.sh build /jboxengine/data`
        - JuliaBox components: `JuliaBox/scripts/install/img_create.sh jbox`
6. Create database. Run: `JuliaBox/scripts/install/create_tables_sqlite.py /jboxengine/data/db/juliabox.db`
7. Run JuliaBox:
    - To start: `JuliaBox/scripts/run/start.sh`
    - To stop: `JuliaBox/scripts/run/stop.sh`
    - If starting JuliaBox after a system reboot, re-mount the loopback devices by running `mount_fs.sh` as specified in the configuration step above.

### Single Machine Multi User Setup
1. If you wish to control CPU and RAM usage in containers:
    - Follow the instructions under section "Adjust memory and swap accounting" from <https://docs.docker.com/installation/ubuntulinux/>
2. JuliaBox uses loopback devices to provision user home folders. Most installations are configured for 8 loop devices by default, some of which may already be used by other services. Increase it to slightly more than the number of sessions you wish to support:
    - Add "max_loop=64" to GRUB_CMDLINE_LINUX in file "/etc/default/grub". Replace 64 with an appropriate number.
    - Run `sudo update-grub`
    - Reboot
3. Sign-up for using [Google Identity](https://developers.google.com/identity/) and get the OAuth key and secret to use.
4. Follow steps 1-3 from previous section.
5. Configure JuliaBox:
    - Create a configuration file `/jboxengine/conf/jbox.user` as: <pre>
    {
        "numlocalmax" : 20, # max concurrent users to support
        "numdisksmax" : 30, # max disks (more than sessions to allow for transitions)
        "admin_users" : ['admin@gmail.com'],  # administrator email id
        "websocket_protocol" : "ws",
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
    }
    </pre>
    - Run `JuliaBox/scripts/install/jbox_configure.sh` to generate JuliaBox configuration files.
    - Run `sudo JuliaBox/scripts/install/mount_fs.sh /jboxengine/data 30 500 ${USER}` to create loopback devices for JuliaBox user home volumes.
6. Follow steps 5-7 from previous section.

### AWS Cluster Setup

TODO