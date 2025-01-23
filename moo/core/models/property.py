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

    #: Name of the Property
    name = models.CharField(max_length=255, db_index=True)
    #: Value of the Property
    value = models.TextField(blank=True, null=True)
    #: Type of the Property
    type = models.CharField(max_length=255, choices=[(x, x) for x in ("string", "python", "dynamic")])
    #: The owner of this Property. Changes require `entrust` permission.
    owner = models.ForeignKey("Object", related_name="+", null=True, on_delete=models.SET_NULL)
    #: The object on which this Property is defined
    origin = models.ForeignKey("Object", related_name="properties", on_delete=models.CASCADE)
    #: If True, this Property’s owner will be reassigned on child instances
    inherited = models.BooleanField(default=False)

    __original_inherited = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_inherited = self.inherited

    @property
    def kind(self):
        return "property"

    def __str__(self):
        return "%s {#%s on %s}" % (self.name, self.id, self.origin)

    def save(self, *args, **kwargs):
        needs_default_permissions = self.pk is None
        super().save(*args, **kwargs)
        if self.inherited and not self.__original_inherited:
            for child in self.origin.get_descendents():  # pylint: disable=no-member
                AccessibleProperty.objects.update_or_create(
                    name=self.name,
                    origin=child,
                    defaults=dict(
                        owner=child.owner,
                        inherited=self.inherited,
                    ),
                    create_defaults=dict(
                        owner=child.owner,
                        inherited=self.inherited,
                        value=self.value,
                        type=self.type,
                    ),
                )
        if not needs_default_permissions:
            return
        utils.apply_default_permissions(self)


class AccessibleProperty(Property):
    class Meta:
        proxy = True
