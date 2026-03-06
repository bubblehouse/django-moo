# -*- coding: utf-8 -*-
"""
Celery configuration for the moo project.
https://docs.celeryq.dev/en/stable/userguide/configuration.html
"""

import os

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
accept_content = ["moojson", "json"]
event_serializer = "moojson"
task_serializer = "moojson"
result_serializer = "moojson"
result_backend = "django-db"
cache_backend = "default"
beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
task_time_limit = 3
broker_connection_retry_on_startup = True

logging = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s: %(levelname)s %(message)s",
        },
        "celeryTask": {
            "()": "celery.app.log.TaskFormatter",
            "fmt": "%(asctime)s: %(levelname)s %(task_name)s[%(task_id)s]: %(message)s",
        },
        "celeryProcess": {"()": "celery.utils.log.ColorFormatter", "fmt": "%(asctime)s: %(levelname)s %(message)s"},
    },
    "filters": {
        "celeryTask": {
            "()": "moo.logging.CeleryTaskFilter",
        },
        "celeryProcess": {
            "()": "moo.logging.CeleryProcessFilter",
        },
        "notCelery": {
            "()": "moo.logging.NotCeleryFilter",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "filters": ["notCelery"],
        },
        "console2": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "celeryTask",
            "filters": ["celeryTask"],
        },
        "console3": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "celeryProcess",
            "filters": ["celeryProcess"],
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "console2", "console3"],
            "level": "INFO",
            "propagate": False,
        }
    },
}
