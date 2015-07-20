#! /usr/bin/env bash
# Add swap

echo "Adding swap of size $1 MB"

dd if=/dev/zero of=/mnt/swapfile bs=1M count=$1
chown root:root /mnt/swapfile
chmod 600 /mnt/swapfile
mkswap /mnt/swapfile
swapon /mnt/swapfile
