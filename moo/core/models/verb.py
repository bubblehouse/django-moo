# -*- coding: utf-8 -*-
"""
Verb model
"""

import logging

from django.core import validators
from django.db import models

from .. import utils
from ..code import interpret
from .acl import AccessibleMixin

log = logging.getLogger(__name__)


class Verb(models.Model, AccessibleMixin):
    #: The Python code for this Verb
    code = models.TextField(blank=True, null=True)
    #: Optional Git repo this code is from
    repo = models.ForeignKey("Repository", related_name="+", blank=True, null=True, on_delete=models.SET_NULL)
    #: Optional name of the code file within the repo
    filename = models.CharField(max_length=255, blank=True, null=True)
    #: Optional Git ref of the code file within the repo
    ref = models.CharField(max_length=255, blank=True, null=True)
    #: The owner of this Verb. Changes require `entrust` permission.
    owner = models.ForeignKey("Object", related_name="+", blank=True, null=True, on_delete=models.SET_NULL)
    #: The object on which this Verb is defined
    origin = models.ForeignKey("Object", related_name="verbs", on_delete=models.CASCADE)
    #: If True, this verb can only be used by the object it is defined on
    ability = models.BooleanField(default=False)
    #: If True, this verb can be invoked by other verbs
    method = models.BooleanField(default=False)

    def __str__(self):
        return "%s {#%s on %s}" % (self.annotated(), self.id, self.origin)

    @property
    def kind(self):
        return "verb"

    def annotated(self):
        ability_decoration = ["", "@"][int(self.ability)]
        method_decoration = ["", "()"][int(self.method)]
        verb_name = self.name()
        return "".join([ability_decoration, verb_name, method_decoration])

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
        if not (self.method):
            raise RuntimeError("%s is not a method." % self)
        if hasattr(self, "invoked_name"):
            l = list(args)
            l.insert(0, self.invoked_name)
            args = tuple(l)
        result = interpret(self.code, *args, **kwargs)
        return result


class VerbName(models.Model):
    verb = models.ForeignKey(Verb, related_name="names", on_delete=models.CASCADE)
    name = models.CharField(max_length=255, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint("verb", "name", name="unique_verb_name")]

    def __str__(self):
        return "%s {#%s on %s}" % (self.name, self.verb.id, self.verb.origin)


# TODO: add support for additional URL types and connection details
class URLField(models.CharField):
    default_validators = [validators.URLValidator(schemes=["https"])]


class Repository(models.Model):
    slug = models.SlugField()
    url = URLField(max_length=255)
    prefix = models.CharField(max_length=255)
