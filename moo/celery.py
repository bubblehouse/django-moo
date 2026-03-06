# -*- coding: utf-8 -*-
"""
Celery workers run the verb tasks.
"""

from celery import Celery
from celery.signals import setup_logging
from kombu.serialization import register

from . import celeryconfig
from .core import moojson

app = Celery("moo")
app.config_from_object("moo.celeryconfig")
app.autodiscover_tasks()

register("moojson", moojson.dumps, moojson.loads, content_type="application/x-moojson", content_encoding="utf-8")


@setup_logging.connect
def configure_celery_logging(**_kwargs):
    from logging.config import dictConfig

    dictConfig(celeryconfig.logging)
