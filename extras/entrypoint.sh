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
elif [ "$1" = 'webssh' ]; then
    exec wssh --port=8422 --hostfile=/etc/ssh/pregenerated_known_hosts --policy=reject
elif [ "$1" = 'celery' ]; then
    if [ "$2" = 'beat' ]; then
        exec celery -A moo beat --uid 33 -l INFO
    elif [ "$2" = 'worker' ]; then
        exec celery -A moo worker -E --uid 33 -l INFO
    else
        exec watchmedo auto-restart -p '.reload' -- celery -A moo worker -E --uid 33 -B -l INFO
    fi
else
    exec "$@"
fi
