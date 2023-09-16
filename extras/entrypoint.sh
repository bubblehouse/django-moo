#!/bin/bash

export PATH="/bin:/usr/bin:/usr/sbin:/usr/local/bin"

cd /usr/src/app

if [ "$1" = '' ]; then
    exec uwsgi --ini /etc/uwsgi.ini
elif [ "$1" = 'manage.py' ]; then
    exec python3.10 "$@"
else
    exec "$@"
fi
