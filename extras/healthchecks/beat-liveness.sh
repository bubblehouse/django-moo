#!/bin/sh

if [ ! -f /var/run/beat-liveness.pid ]; then
    echo "Celery beat PID file NOT found."
    exit 1
fi

echo "Celery beat PID file found."
