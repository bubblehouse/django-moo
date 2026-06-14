# -*- coding: utf-8 -*-
"""
Indexed external-key resolution (spec 200, item B).

Bootstrap generation resolves objects by a stable external key
(``zone_slug``, ``location_slug``, a ZIL object id).  ``Property.value`` is
unindexed, so resolve-by-property is a full scan; this dedicated, indexed
``(namespace, key) -> object`` table gives generators an O(1), idempotent
resolve without bulk-loading — opt-in, rather than indexing every property
value.
"""

from django.db import models


class ExternalKey(models.Model):
    """A stable external identifier mapped to an Object, unique per namespace."""

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "key"], name="externalkey_namespace_key_unique"),
        ]

    namespace = models.CharField(max_length=128)
    key = models.CharField(max_length=255)
    object = models.ForeignKey("Object", related_name="external_keys", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.namespace}:{self.key} -> #{self.object_id}"
