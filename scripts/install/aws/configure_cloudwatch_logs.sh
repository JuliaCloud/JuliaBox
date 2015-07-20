#!/usr/bin/env bash

if [ $# -ne 5 ]
then
    echo "Usage: sudo configure_cloudwatch_logs.sh <log_group_prefix> <jbox_user> <aws_access_key_id> <aws_secret_key> <start_service(0/1)>"
    exit 1
fi

if [ "root" != `whoami` ]
then
    echo "Must be run as superuser"
    exit 1
fi

GROUP_PFX=$1
JBOX_USER=$2
AWS_ACCESS_KEY_ID=$3
AWS_SECRET_KEY=$4
START_SERVICE=$5

service awslogs stop
cat > /var/awslogs/etc/aws.conf <<DELIM
[plugins]
cwlogs = cwlogs
[default]
region = us-east-1
aws_access_key_id = ${AWS_ACCESS_KEY_ID}
aws_secret_access_key = ${AWS_SECRET_KEY}
DELIM

sudo -u ${JBOX_USER} cat > /home/${JBOX_USER}/cloud_watch_logs.cfg <<DELIM
[general]
state_file = /var/awslogs/state/agent-state

[/var/log/syslog]
file = /var/log/syslog
log_group_name = ${GROUP_PFX}/var/log/syslog
log_stream_name = {instance_id}
datetime_format = %b %d %H:%M:%S
initial_position = start_of_file
buffer_duration = 5000

[/home/${JBOX_USER}/JuliaBox/webserver/logs/webserver_err.log]
file = /home/${JBOX_USER}/JuliaBox/webserver/logs/webserver_err.log
log_group_name = ${GROUP_PFX}/webserver/logs/webserver_err.log
log_stream_name = {instance_id}
datetime_format = %Y/%m/%d %H:%M:%S
initial_position = start_of_file
buffer_duration = 5000

[/home/${JBOX_USER}/JuliaBox/engine/engineinteractive_err.log]
file = /home/${JBOX_USER}/JuliaBox/engine/engineinteractive_err.log
log_group_name = ${GROUP_PFX}/engine/engineinteractive_err.log
log_stream_name = {instance_id}
datetime_format = %Y-%m-%d %H:%M:%S,%z
initial_position = start_of_file
buffer_duration = 5000

[/home/${JBOX_USER}/JuliaBox/engine/enginedaemon_err.log]
file = /home/${JBOX_USER}/JuliaBox/engine/enginedaemon_err.log
log_group_name = ${GROUP_PFX}/engine/enginedaemon_err.log
log_stream_name = {instance_id}
datetime_format = %Y-%m-%d %H:%M:%S,%z
initial_position = start_of_file
buffer_duration = 5000

[/home/${JBOX_USER}/JuliaBox/engine/engineinteractive.log]
file = /home/${JBOX_USER}/JuliaBox/engine/engineinteractive.log
log_group_name = ${GROUP_PFX}/engine/engineinteractive.log
log_stream_name = {instance_id}
datetime_format = %Y-%m-%d %H:%M:%S,%z
initial_position = start_of_file
buffer_duration = 5000

[/home/${JBOX_USER}/JuliaBox/engine/enginedaemon.log]
file = /home/${JBOX_USER}/JuliaBox/engine/enginedaemon.log
log_group_name = ${GROUP_PFX}/engine/enginedaemon.log
log_stream_name = {instance_id}
datetime_format = %Y-%m-%d %H:%M:%S,%z
initial_position = start_of_file
buffer_duration = 5000
DELIM

wget https://s3.amazonaws.com/aws-cloudwatch/downloads/latest/awslogs-agent-setup.py
chmod +x ./awslogs-agent-setup.py
./awslogs-agent-setup.py -n -r us-east-1 -c /home/${JBOX_USER}/cloud_watch_logs.cfg

if [ $START_SERVICE -eq 1 ]
then
    service awslogs start
fi