#!/bin/bash

export PATH="/bin:/usr/bin:/usr/sbin:/usr/local/bin"

cd /usr/src/app

if [ "$1" = '' ]; then
    exec uwsgi --ini /etc/uwsgi.ini
elif [ "$1" = 'manage.py' ]; then
    if [ "$2" = 'moo_shell' ]; then
        exec watchmedo auto-restart -p '.reload' -- python3.11 "$@"
    else
        exec python3.11 "$@"
    fi
else
    exec "$@"
fi
