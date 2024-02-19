from django.db import models

from .acl import AccessibleMixin
from .. import utils

class Property(models.Model):
    class Meta:
        verbose_name_plural = 'properties'

    name = models.CharField(max_length=255)
    value = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, choices=[(x,x) for x in ('string', 'python', 'dynamic')])
    owner = models.ForeignKey("Object", related_name='+', null=True, on_delete=models.SET_NULL)
    origin = models.ForeignKey("Object", related_name='properties', on_delete=models.CASCADE)
    inherited = models.BooleanField(default=False)

    __original_inherited = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_inherited = self.inherited

    @property
    def kind(self):
        return 'property'

    def __str__(self):
        return '%s {#%s on %s}' % (self.name, self.id, self.origin)

    def save(self, *args, **kwargs):
        needs_default_permissions = self.pk is None
        super().save(*args, **kwargs)
        if self.inherited and not self.__original_inherited:
            for child in self.origin.get_descendents():
                AccessibleProperty.objects.update_or_create(
                    name = self.name,
                    origin = child,
                    defaults = dict(
                        owner = child.owner,
                        inherited = self.inherited,
                    ),
                    create_defaults = dict(
                        owner = child.owner,
                        inherited = self.inherited,
                        value = self.value,
                        type = self.type,
                    )
                )
        if not needs_default_permissions:
            return
        utils.apply_default_permissions(self)

class AccessibleProperty(Property, AccessibleMixin):
    class Meta:
        proxy = True
