# -*- coding: utf-8 -*-
"""
Access control list functionality for Object, Verbs and Properties.
"""

import logging

from django.db import models

from .. import code

_PERM_ID_CACHE_KEY = "__permission_id_cache__"


def _get_permission_id(name: str) -> int:
    """
    Return the pk for a named Permission, caching in the per-session perm_cache.
    The Permission table is static after bootstrap, so one lookup per session suffices.
    Falls back to a direct DB query outside a ContextManager session.
    """
    cache = code.ContextManager.get_perm_cache()
    if cache is not None:
        perm_ids = cache.setdefault(_PERM_ID_CACHE_KEY, {})
        if name in perm_ids:
            return perm_ids[name]
        pk = Permission.objects.get(name=name).id
        perm_ids[name] = pk
        return pk
    return Permission.objects.get(name=name).id

log = logging.getLogger(__name__)


class AccessibleMixin:
    """
    The base class for all Objects, Verbs, and Properties.
    """

    def can_caller(self, permission, subject):
        """
        Check if the current caller has permission for something.
        """
        caller = code.ContextManager.get("caller")
        if not caller:
            return
        if permission == "grant" and caller.owns(subject):
            return
        caller.is_allowed(permission, subject, fatal=True)

    def allow(self, accessor, permission):
        """
        Allow a certain object or group to do something on this object.

        [ACL] allowed to grant on this (or owner of this)
        """
        self.can_caller("grant", self)
        Access.objects.create(
            object=self if self.kind == "object" else None,
            verb=self if self.kind == "verb" else None,
            property=self if self.kind == "property" else None,
            rule="allow",
            permission_id=_get_permission_id(permission),
            type="group" if isinstance(accessor, str) else "accessor",
            accessor=None if isinstance(accessor, str) else accessor,
            group=accessor if isinstance(accessor, str) else None,
        )

    def deny(self, accessor, permission):
        """
        Deny a certain object or group from doing something on this object.

        [ACL] allowed to grant on this (or owner of this)
        """
        self.can_caller("grant", self)
        Access.objects.create(
            object=self if self.kind == "object" else None,
            verb=self if self.kind == "verb" else None,
            property=self if self.kind == "property" else None,
            rule="deny",
            permission_id=_get_permission_id(permission),
            type="group" if isinstance(accessor, str) else "accessor",
            accessor=None if isinstance(accessor, str) else accessor,
            group=accessor if isinstance(accessor, str) else None,
        )
        # Evict any cached True results for this subject — a new deny rule may flip them.
        cache = code.ContextManager.get_perm_cache()
        if cache is not None:
            evict = [k for k in cache if k[0] == "perm" and k[3] == self.kind and k[4] == self.pk]
            for k in evict:
                del cache[k]


class Permission(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):  # pylint: disable=invalid-str-returned
        return self.name


class Access(models.Model):
    class Meta:
        verbose_name_plural = "access controls"
        unique_together = ("object", "verb", "property", "rule", "permission", "type", "accessor", "group", "weight")
        indexes = [
            models.Index(fields=["object", "permission"], name="access_object_permission_idx"),
            models.Index(fields=["verb", "permission"], name="access_verb_permission_idx"),
            models.Index(fields=["property", "permission"], name="access_property_permission_idx"),
        ]

    object = models.ForeignKey("Object", related_name="acl", null=True, on_delete=models.CASCADE)
    verb = models.ForeignKey("Verb", related_name="acl", null=True, on_delete=models.CASCADE)
    property = models.ForeignKey("Property", related_name="acl", null=True, on_delete=models.CASCADE)
    rule = models.CharField(max_length=5, choices=[(x, x) for x in ("allow", "deny")])
    permission = models.ForeignKey(Permission, related_name="usage", on_delete=models.CASCADE)
    type = models.CharField(max_length=8, choices=[(x, x) for x in ("accessor", "group")])
    accessor = models.ForeignKey("Object", related_name="rights", null=True, on_delete=models.CASCADE)
    group = models.CharField(max_length=8, null=True, choices=[(x, x) for x in ("everyone", "owners", "wizards")])
    weight = models.IntegerField(default=0)

    def actor(self):
        return self.accessor if self.type == "accessor" else self.group

    def entity(self):
        if self.object:
            return "self"
        elif self.verb:
            return "".join(
                [
                    ["", "@"][self.verb.ability],  # pylint: disable=no-member
                    self.verb.names.all()[:1][0].name,
                    ["", "()"][self.verb.method],  # pylint: disable=no-member
                ]
            )
        else:
            return self.property.name

    def origin(self):
        if self.object:
            return self.object
        elif self.verb:
            return self.verb.origin  # pylint: disable=no-member
        else:
            return self.property.origin  # pylint: disable=no-member

    def _get_entity(self):
        if self.object_id:
            return self.object
        if self.verb_id:
            return self.verb
        if self.property_id:
            return self.property
        return None

    def save(self, *args, **kwargs):
        entity = self._get_entity()
        if entity is not None:
            entity.can_caller("grant", entity)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        entity = self._get_entity()
        if entity is not None:
            entity.can_caller("grant", entity)
        super().delete(*args, **kwargs)

    def __str__(self):
        return "%(rule)s %(actor)s %(permission)s on %(entity)s (%(weight)s)" % dict(
            rule=self.rule,
            actor=self.actor(),
            permission=self.permission.name,
            entity=self.entity(),
            weight=self.weight,
        )
