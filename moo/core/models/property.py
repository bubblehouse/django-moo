# -*- coding: utf-8 -*-
"""
Property model
"""

from django.db import models

from .. import utils
from .acl import AccessibleMixin


class Property(models.Model, AccessibleMixin):
    class Meta:
        verbose_name_plural = "properties"
        indexes = [
            models.Index(fields=["origin", "name"], name="property_origin_name_idx"),
        ]

    #: Name of the Property. Unique per ``origin``.
    name = models.CharField(max_length=255, db_index=True)
    #: Serialised value of the Property. ``Object.get_property()`` returns
    #: the deserialised Python value; read this field directly only when
    #: you need the raw moojson representation.
    value = models.TextField(blank=True, null=True)
    #: One of ``string``, ``python``, or ``dynamic``. Controls how
    #: ``value`` is decoded.
    type = models.CharField(max_length=255, choices=[(x, x) for x in ("string", "python", "dynamic")])
    #: The Object that owns this Property row. Changes require ``entrust``
    #: permission.
    owner = models.ForeignKey("Object", related_name="+", null=True, on_delete=models.SET_NULL)
    #: The Object the Property is defined on. Inheritance copies the
    #: Property to descendants when they're created.
    origin = models.ForeignKey("Object", related_name="properties", on_delete=models.CASCADE)
    #: If ``True``, descendants keep the parent's ``owner`` when they
    #: inherit the Property. If ``False`` (the default), each descendant's
    #: row is owned by the descendant's owner. See
    #: :doc:`/reference/properties` for the LambdaMOO ``c``-bit equivalent
    #: and when to use it.
    inherit_owner = models.BooleanField(default=False)

    __original_inherit_owner = None
    _original_owner_id = None
    _original_value = None
    _original_type = None
    _original_name = None

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if "owner_id" in field_names:
            instance._original_owner_id = values[field_names.index("owner_id")]  # pylint: disable=protected-access
        if "value" in field_names:
            instance._original_value = values[field_names.index("value")]  # pylint: disable=protected-access
        if "type" in field_names:
            instance._original_type = values[field_names.index("type")]  # pylint: disable=protected-access
        if "name" in field_names:
            instance._original_name = values[field_names.index("name")]  # pylint: disable=protected-access
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_inherit_owner = self.inherit_owner

    @property
    def kind(self):
        return "property"

    def __str__(self):
        return "%s {#%s on %s}" % (self.name, self.id, self.origin)

    def save(self, *args, **kwargs):
        needs_default_permissions = self.pk is None
        if needs_default_permissions:
            # New property: check write on the origin object (no ACL rows exist yet for self)
            self.origin.can_caller("write", self.origin)  # pylint: disable=no-member
        else:
            # `write` is only required when a non-owner field changed. Owner changes have
            # their own granular `entrust` check; with that alone, a caller can transfer
            # ownership without needing `write` on the property.
            non_owner_changed = (
                self.value != self._original_value
                or self.type != self._original_type
                or self.name != self._original_name
                or self.inherit_owner != self.__original_inherit_owner
            )
            if non_owner_changed:
                self.origin.can_caller("write", self)  # pylint: disable=no-member
            if self._original_owner_id != self.owner_id:
                self.origin.can_caller("entrust", self)  # pylint: disable=no-member
        super().save(*args, **kwargs)
        if self.inherit_owner and not self.__original_inherit_owner:
            for child in self.origin.get_descendents():  # pylint: disable=no-member
                Property.objects.update_or_create(
                    name=self.name,
                    origin=child,
                    defaults=dict(
                        owner=child.owner,
                        inherit_owner=self.inherit_owner,
                    ),
                    create_defaults=dict(
                        owner=child.owner,
                        inherit_owner=self.inherit_owner,
                        value=self.value,
                        type=self.type,
                    ),
                )
        # Re-baseline change-tracking after a successful save.
        self._original_owner_id = self.owner_id
        self._original_value = self.value
        self._original_type = self.type
        self._original_name = self.name
        self.__original_inherit_owner = self.inherit_owner
        if not needs_default_permissions:
            return
        utils.apply_default_permissions(self)

    def delete(self, *args, **kwargs):
        self.origin.can_caller("write", self)  # pylint: disable=no-member
        super().delete(*args, **kwargs)
