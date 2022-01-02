#!/bin/bash
set -e

# || true to ignore if the groups already exist, and continue successfully.
groupadd -r -g $PGID crashserver || true
useradd  -r -u $PUID -g $PGID -m crashserver || true
export HOME=/home/crashserver

exec gosu crashserver:crashserver "$@"
