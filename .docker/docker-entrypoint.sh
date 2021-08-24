#!/bin/sh

# Exit script if any file returned a non-zero exit code
set -e

. /venv/bin/activate
exec gunicorn --bind 0.0.0.0:8888 --forwarded-allow-ips='*' wsgi:app