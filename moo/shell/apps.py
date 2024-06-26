# -*- coding: utf-8 -*-
"""
Django App support
"""

from django.apps import AppConfig


class ShellConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "moo.shell"
