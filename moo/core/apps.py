# -*- coding: utf-8 -*-
"""
Django App support
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "moo.core"
