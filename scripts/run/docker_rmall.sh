#!/bin/sh
for id in `docker ps -a | cut -d" " -f1 | grep -v CONTAINER`; do echo "removing $id..."; docker kill $id; docker rm $id; done