# -*- coding: utf-8 -*-
"""
Indexed external-key resolution.

Bootstrap generation resolves objects by a stable external key
(``zone_slug``, ``location_slug``, a ZIL object id).  ``Property.value`` is
unindexed, so resolve-by-property is a full scan; this dedicated, indexed
``(namespace, key) -> object`` table gives generators an O(1), idempotent
resolve without bulk-loading — opt-in, rather than indexing every property
value.
"""

from django.contrib.sites.models import Site
from django.db import models

from ..managers import _DB_NOT_READY, _current_site
from .acl import WizardGuardedManager


class SiteKeyManager(WizardGuardedManager):
    """The guarded manager, filtered to the active Site the way ``Object.objects`` is."""

    def get_queryset(self):
        queryset = super().get_queryset()
        site = _current_site()
        if site is _DB_NOT_READY:
            return queryset
        if site is None:
            return queryset.none()
        return queryset.filter(site=site)


class ExternalKey(models.Model):
    """A stable external identifier mapped to an Object, unique per Site and namespace."""

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["site", "namespace", "key"], name="externalkey_site_namespace_key_unique"),
        ]

    # Defense-in-depth parity with the other safety tables: non-wizard bulk
    # update/delete is refused. Row creation still follows normal object
    # ownership (a builder generating a keyed world is fine), so save() is not
    # wizard-gated — only the bulk-mutation paths are.
    objects = SiteKeyManager()
    #: Every Site's keys, for cross-universe diagnostics and the SDK, which picks the Site itself.
    global_objects = WizardGuardedManager()

    #: The universe the key belongs to: always the Site of ``object``. Two
    #: universes that bootstrap the same dataset each get their own keys.
    site = models.ForeignKey(Site, related_name="external_keys", on_delete=models.CASCADE)
    namespace = models.CharField(max_length=128)
    key = models.CharField(max_length=255)
    object = models.ForeignKey("Object", related_name="external_keys", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.namespace}:{self.key} -> #{self.object_id}"
