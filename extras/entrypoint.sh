#!/bin/bash

export PATH="/bin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/app/bin"

cd /usr/app/src

if [ "$1" = '' ]; then
    exec opentelemetry-instrument uwsgi --ini /etc/uwsgi.ini
elif [ "$1" = 'manage.py' ]; then
    if [ "$2" = 'moo_shell' ]; then
        exec watchmedo auto-restart -p '.reload' -- /usr/app/bin/python3.11 "$@"
    else
        exec /usr/app/bin/python3.11 "$@"
    fi
elif [ "$1" = 'webssh' ]; then
    SITE_PACKAGES=$(/usr/app/bin/python3.11 -c 'import sys; print(sys.path[-1])')
    envsubst < "$SITE_PACKAGES/webssh/templates/index.html.tmpl" \
             > "$SITE_PACKAGES/webssh/templates/index.html"
    exec wssh --port=8422 --hostfile=/etc/ssh/pregenerated_known_hosts --policy=reject
elif [ "$1" = 'celery' ]; then
    if [ "$2" = 'beat' ]; then
        exec celery -A moo beat -l INFO --pidfile=/tmp/beat-liveness.pid
    elif [ "$2" = 'worker' ]; then
        exec celery -A moo worker -E -l INFO
    else
        exec watchmedo auto-restart -p '.reload' -- celery -A moo worker -E -B -l INFO
    fi
else
    exec "$@"
fi
