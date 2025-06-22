# -*- coding: utf-8 -*-
"""
A game server for hosting text-based online MOO-like games.
"""
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ("celery_app", "get_version")

__version__ = "0.39.0"


def get_version():
    """
    Get the current version of DjangoMOO.
    """
    return __version__
