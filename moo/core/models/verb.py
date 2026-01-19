# -*- coding: utf-8 -*-
"""
Verb model
"""

import logging
import warnings

from django.conf import settings
from django.core import validators
from django.db import models

from .. import utils, lookup
from ..code import interpret
from .acl import AccessibleMixin

log = logging.getLogger(__name__)


class Preposition(models.Model):
    pass


class PrepositionName(models.Model):
    name = models.CharField(max_length=255)
    preposition = models.ForeignKey(Preposition, related_name="names", on_delete=models.CASCADE)


class PrepositionSpecifier(models.Model):
    preposition = models.ForeignKey(Preposition, related_name="+", on_delete=models.SET_NULL, blank=True, null=True)
    preposition_specifier = models.CharField(
        max_length=255,
        choices=settings.PREPOSITION_SPECIFIER_CHOICES,
        db_index=True,
    )
    specifier = models.CharField(
        max_length=255, choices=settings.OBJECT_SPECIFIER_CHOICES, db_index=True, default="none"
    )


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
    #: If the Verb can be called with a direct obect
    direct_object = models.CharField(
        max_length=255, choices=settings.OBJECT_SPECIFIER_CHOICES, db_index=True, default="none", db_default="none"
    )
    #: If the Verb can be called with an indirect obect
    indirect_objects = models.ManyToManyField(PrepositionSpecifier, related_name="+", blank=True)

    def __str__(self):
        return "%s {#%s on %s}" % (self.annotated(), self.id, self.origin)

    @property
    def kind(self):
        return "verb"

    @property
    def is_ability(self):
        return self.direct_object == "this" and self.indirect_objects is None

    @property
    def is_method(self):
        return self.direct_object is None and self.indirect_objects is not None

    def annotated(self):
        ability_decoration = ["", "@"][int(self.is_ability)]
        method_decoration = ["", "()"][int(self.is_method)]
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

    def is_bound(self):
        return hasattr(self, "invoked_object") and hasattr(self, "invoked_name")

    def passthrough(self, *args, **kwargs):
        """
        Invoke this verb on the parent objects, if they exist.

        Often, it is useful for a child object to define a verb that augments the behavior of a verb on its parent
        object. For example, in the LambdaCore database, the root object (which is an ancestor of every other object)
        defines a verb called `description' that simply returns the value of this.description; this verb is used by
        the implementation of the look command. In many cases, a programmer would like the description of some object
        to include some non-constant part; for example, a sentence about whether or not the object was `awake' or
        `sleeping'. This sentence should be added onto the end of the normal description. The programmer would like to
        have a means of calling the normal description verb and then appending the sentence onto the end of that
        description. The function `passthrough()` is for exactly such situations.

        passthrough calls the verb with the same name as the current verb but as defined on the parent of the object
        that defines the current verb. The arguments given to passthrough are the ones given to the called verb and the
        returned value of the called verb is returned from the call to passthrough. The initial value of `this` in the
        called verb is the same as in the calling verb.

        Thus, in the example above, the child-object's description verb might have the following implementation:

            return passthrough() + "  It is " + (this.awake ? "awake." | "sleeping.")

        That is, it calls its parent's description verb and then appends to the result a sentence whose content is
        computed based on the value of a property on the object.

        In almost all cases, you will want to call `passthrough()' with the same arguments as were given to the current
        verb. This is easy to write in Python; just call passthrough(*args).
        """
        if not self.is_bound():
            raise RuntimeError("Cannot use passthrough on an unbound verb.")

        # the origin is where the verb is defined, not where it was found
        parents = self.origin.parents.all()
        for parent in parents:
            if parent.has_verb(self.invoked_name):
                verb = parent.get_verb(self.invoked_name)
                verb.invoked_object = self.invoked_object
                verb.invoked_name = self.invoked_name
                assert verb != self, "Infinite passthrough loop detected."
                return verb(*args, **kwargs)
        warnings.warn(
            "Passthrough ignored: no parent has verb %s" % self.invoked_name,
            RuntimeWarning,
        )

    def __call__(self, *args, **kwargs):
        this = None
        name = "__main__"
        if self.is_bound():
            this = self.invoked_object
            name = self.invoked_name
        if self.filename is not None:
            kwargs['filename'] = self.filename
        system = lookup(1)
        result = interpret(self.code, name, this, self.passthrough, system, *args, **kwargs)
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
