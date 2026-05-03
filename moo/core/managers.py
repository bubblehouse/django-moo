# -*- coding: utf-8 -*-
"""
Site-scoped QuerySet manager for multi-universe support.
"""

from django.db import models
from django.db.utils import OperationalError, ProgrammingError

# Sentinel returned by _current_site() when the database isn't available
# (Django app initialization, pre-migration). This is distinguished from
# `None` (a real "no site context" condition at runtime) so SiteManager
# can fail open during init but fail closed during normal operation.
_DB_NOT_READY = object()


def get_default_site():
    """
    Return the configured default Site (``Site.objects.get(pk=SITE_ID)``).

    Uses Django's site cache (``Site.objects.clear_cache()`` is invoked
    automatically on Site save), so repeated calls don't hit the DB.
    """
    from django.conf import settings
    from django.contrib.sites.models import Site

    return Site.objects.get(pk=getattr(settings, "SITE_ID", 1))


def _current_site():
    """
    Return the active Site for the current context, the configured default
    Site, ``_DB_NOT_READY`` if the DB isn't available, or ``None`` if the
    default Site row is missing.
    """
    # Imports inside the function to dodge circular-import issues during
    # Django app initialization.
    from django.contrib.sites.models import Site

    from .code import ContextManager

    site = ContextManager.get_site()
    if site is not None:
        return site
    try:
        return get_default_site()
    except (OperationalError, ProgrammingError):
        # DB tables not yet created (e.g. initial migration).
        return _DB_NOT_READY
    except Site.DoesNotExist:
        # SITE_ID points at a missing row — caller fails closed.
        return None


class SiteManager(models.Manager):
    """Manager that automatically filters Objects to the current site."""

    def get_queryset(self):
        site = _current_site()
        if site is _DB_NOT_READY:
            # App init / pre-migration — return everything so Django's own
            # bootstrapping queries (introspection, content types) work.
            return super().get_queryset()
        if site is None:
            # Runtime "no site available" — fail closed so a missing
            # default Site can never silently leak rows across universes.
            return super().get_queryset().none()
        return super().get_queryset().filter(site=site)
