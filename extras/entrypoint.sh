#!/bin/bash

export PATH="/bin:/usr/bin:/usr/sbin:/usr/local/bin"

cd /usr/src/app

if [ "$1" = '' ]; then
    exec poetry run uwsgi --ini /etc/uwsgi.ini
elif [ "$1" = 'manage.py' ]; then
    exec poetry run python3.10 "$@"
else
    exec "$@"
fi
