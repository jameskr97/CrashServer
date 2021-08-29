#!/bin/bash

# Exit script if any file returned a non-zero exit code
set -e
. /venv/bin/activate

# If the exit code is positive, then exit
if ! python3 init.py; then
     exit 1
fi

exec gunicorn --bind 0.0.0.0:8888 --forwarded-allow-ips='*' wsgi:app