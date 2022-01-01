#!/bin/bash
set -e

gruopadd -r -g $PGID crashserver
useradd  -r -u $PUID -g $PGID -m crashserver
export HOME=/home/crashserver

exec gosu crashserver:crashserver "$@"
