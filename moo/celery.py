# -*- coding: utf-8 -*-
"""
Celery workers run the verb tasks.
"""

from celery import Celery
from kombu.serialization import register

from .core import moojson

app = Celery("moo")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

register("moojson", moojson.dumps, moojson.loads, content_type="application/x-moojson", content_encoding="utf-8")
