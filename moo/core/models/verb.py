from django.db import models
from django.core import validators

from ..code import context, interpret
from .acl import AccessibleMixin
from .. import api, utils

class Verb(models.Model, AccessibleMixin):
    code = models.TextField(blank=True, null=True)
    repo = models.ForeignKey("Repository", related_name='+', blank=True, null=True, on_delete=models.SET_NULL)
    filename = models.CharField(max_length=255, blank=True, null=True)
    ref = models.CharField(max_length=255, blank=True, null=True)
    owner = models.ForeignKey("Object", related_name='+', blank=True, null=True, on_delete=models.SET_NULL)
    origin = models.ForeignKey("Object", related_name='verbs', on_delete=models.CASCADE)
    ability = models.BooleanField(default=False)
    method = models.BooleanField(default=False)

    def __str__(self):
        return "%s {#%s on %s}" % (
            self.annotated(), self.id, self.origin
        )

    @property
    def kind(self):
        return 'verb'

    def annotated(self):
        ability_decoration = ['', '@'][self.ability]
        method_decoration = ['', '()'][self.method]
        verb_name = self.name()
        return ''.join([ability_decoration, verb_name, method_decoration])

    def name(self):
        names = self.names.all()
        if not names:
            return "(untitled)"
        return names[0].name

    def save(self, *args, **kwargs):
        needs_default_permissions = self.pk is None
        super().save(*args, **kwargs)
        if not needs_default_permissions:
            return
        utils.apply_default_permissions(self)

class AccessibleVerb(Verb):
    class Meta:
        proxy = True

    def __call__(self, *args, **kwargs):
        if not(self.method):
            raise RuntimeError("%s is not a method." % self)
        result = interpret(context.get('caller'), context.get('writer'),
                           self.code, *args, **kwargs)
        return result


class VerbName(models.Model):
    verb = models.ForeignKey(Verb, related_name='names', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint("verb", "name", name="unique_verb_name")
        ]

    def __str__(self):
        return "%s {#%s on %s}" % (
            self.name, self.verb.id, self.verb.origin
        )

# TODO: add support for additional URL types and connection details
class URLField(models.CharField):
    default_validators = [validators.URLValidator(schemes=['https'])]

class Repository(models.Model):
    slug = models.SlugField()
    url = URLField(max_length=255)
    prefix = models.CharField(max_length=255)
