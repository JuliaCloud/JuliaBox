## Installation Scripts
- `install/sys_install.sh`: Installs required packages on a base Ubuntu system
- `install/img_create.sh`: Creates / pulls JuliaBox Docker image and user home directory image
- `install/mount_fs.sh`: Creates and mounts loopback disks to be used as user home directories. Requires number of disks to create, and size of each disk (in MB) as parameters. Allocate a few more disks than the maximum number of containers, to take care of the delay of backing up of stopped containers. Allocate at least 500MB for user home directories, to provide enough space for Julia packages.
- `install/unmount_fs.sh`: Unmounts and deletes the loopback disks.
- `install/jbox_configure.sh`: Configure JuliaBox server.
- `install/create_tables_dynamodb.py`: Create required DynamoDB tables.

## Scripts for Starting / Stopping JuliaBox
- `run/start.sh`
- `run/stop.sh`
- `run/reload.sh`: Re-start the server and apply any changes made to configuration.
- `run/clean.sh`: Remove all log files.

## Scripts for Maintenance / Troubleshooting
- `maintain/upload_user_home.py`: Upload the JuliaBox user home image from local (build) system on to S3 and update relevant table. Used to apply updated Julia packages on to a running cluster.
- `maintain/log_tools.py`: Search archived CloudWatch logs for troubleshooting issues.
