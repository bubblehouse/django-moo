# -*- coding: utf-8 -*-
"""
Site-scoped QuerySet manager for multi-universe support.
"""

from django.db import models


def _current_site():
    """
    Return the active Site for the current context, or fall back to the default.
    Returns None if the database is not yet available (e.g. during app initialization
    or before migrations have run).
    """
    # Import here to avoid circular imports
    from .code import ContextManager
    from django.contrib.sites.models import Site
    from django.conf import settings

    site = ContextManager.get_site()
    if site is not None:
        return site
    # Fall back to the configured default site
    try:
        return Site.objects.get_current()
    except Exception:  # pylint: disable=broad-except
        # DB not yet available (app init, pre-migration, tests without DB setup)
        return None


class SiteManager(models.Manager):
    """Manager that automatically filters Objects to the current site."""

    def get_queryset(self):
        """Return only objects belonging to the current site."""
        site = _current_site()
        if site is None:
            # No site context available — return unfiltered queryset
            # (happens during app initialization before DB is ready)
            return super().get_queryset()
        return super().get_queryset().filter(site=site)
