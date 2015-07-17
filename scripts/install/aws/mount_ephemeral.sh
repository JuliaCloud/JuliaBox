#! /usr/bin/env bash

if [ "root" != `whoami` ]
then
    echo "Must be run as superuser"
    exit 1
fi

service docker stop
sleep 5
mkfs -t ext4 -m 1 -v $1
mkdir /jboxengine
mount $1 /jboxengine
