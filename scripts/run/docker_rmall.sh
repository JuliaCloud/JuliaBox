#!/bin/sh

echo "killing all containers..."
docker kill $(docker ps -a -q)

echo "removing stopped containers..."
docker rm $(docker ps -a -q)

echo "removing untagged images..."
docker rmi $(docker images | grep "^<none>" | awk '{print $3}')