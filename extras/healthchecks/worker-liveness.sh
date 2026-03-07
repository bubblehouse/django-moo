#!/bin/sh

LIVENESS_FILE=/var/run/worker-liveness

if [ ! -f "$LIVENESS_FILE" ]; then
    echo "Celery liveness file NOT found."
    exit 1
fi

file_time=$(stat -c %Y "$LIVENESS_FILE")
now=$(date +%s)
time_diff=$((now - file_time))

if [ "$time_diff" -gt 60 ]; then
    echo "Celery Worker liveness file timestamp DOES NOT matches the given constraint."
    exit 1
fi

echo "Celery Worker liveness file found and timestamp matches the given constraint."
