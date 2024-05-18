# -*- coding: utf-8 -*-
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app', 'get_version')

__version__ = "0.21.0"

def get_version():
    return __version__
