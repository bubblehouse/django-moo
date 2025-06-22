# -*- coding: utf-8 -*-
"""
The primary Object class
"""

import json
import logging
from typing import Generator

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .. import bootstrap, exceptions, invoke, utils
from ..code import context
from .acl import Access, AccessibleMixin, Permission
from .auth import Player
from .property import AccessibleProperty
from .verb import AccessibleVerb, Preposition, PrepositionName, PrepositionSpecifier, VerbName

log = logging.getLogger(__name__)


@receiver(m2m_changed)
def relationship_changed(sender, instance, action, model, signal, reverse, pk_set, using, **kwargs):
    child = instance
    if not (sender is Relationship and not reverse):
        return
    elif action in ("pre_add", "pre_remove"):
        child.can_caller("transmute", instance)
        for pk in pk_set:
            parent = model.objects.get(pk=pk)
            parent.can_caller("derive", parent)
        return
    elif action != "post_add":
        return
    for pk in pk_set:
        parent = model.objects.get(pk=pk)
        # pylint: disable=redefined-builtin
        for property in AccessibleProperty.objects.filter(origin=parent, inherited=True):
            AccessibleProperty.objects.update_or_create(
                name=property.name,
                origin=child,
                defaults=dict(
                    owner=child.owner,
                    inherited=property.inherited,
                ),
                create_defaults=dict(
                    owner=child.owner,
                    inherited=property.inherited,
                    value=property.value,
                    type=property.type,
                ),
            )


class Object(models.Model, AccessibleMixin):
    #: The canonical name of the object
    name = models.CharField(max_length=255, db_index=True)
    #: If True, this object is the only object with this name
    unique_name = models.BooleanField(default=False, db_index=True)
    #: This object should be obvious among a group. The meaning of this value is database-dependent.
    obvious = models.BooleanField(default=True)
    #: The owner of this object. Changes require `entrust` permission.
    owner = models.ForeignKey("self", related_name="+", blank=True, null=True, on_delete=models.SET_NULL)
    parents = models.ManyToManyField(
        "self",
        related_name="children",
        blank=True,
        symmetrical=False,
        through="Relationship",
    )
    """
    The parents of this object. Changes require `derive` and `transmute` permissions, respectively.

    .. code-block:: Python

        from moo.core import api, lookup
        # in the default DB, all wizards inherit from this Object
        wizard_class = lookup("wizard class")
        # Changes to ManyToMany fields like this are automatically saved
        api.caller.parents.add(wizard_class)
    """
    location = models.ForeignKey(
        "self",
        related_name="contents",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        db_index=True,
    )
    """
    The location of this object. When changing, this kicks off some other verbs:

    If `where` is the new object, then the verb-call `where.accept(self)` is performed before any movement takes place.
    If the verb returns a false value and the programmer is not a wizard, then `where` is considered to have refused entrance
    to `self` and raises :class:`.PermissionError`. If `where` does not define an `accept` verb, then it is treated as if
    it defined one that always returned false.

    If moving `what` into `self` would create a loop in the containment hierarchy (i.e., what would contain itself, even
    indirectly), then :class:`.RecursiveError` is raised instead.

    Let `old` be the location of `self` before it was moved. If `old` is a valid object, then the verb-call
    `old.exitfunc(self)` is performed and its result is ignored; it is not an error if `old` does not define
    a verb named `exitfunc`.

    Finally, if `where` is still the location of `self`, then the verb-call `where.enterfunc(self)` is performed and its
    result is ignored; again, it is not an error if `where` does not define a verb named `enterfunc`.
    """

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance.original_owner = values[field_names.index("owner_id")]
        instance.original_location = values[field_names.index("location_id")]
        return instance

    def __str__(self):
        return "#%s (%s)" % (self.id, self.name)

    @property
    def kind(self):
        return "object"

    def is_named(self, name: str) -> bool:
        """
        Check if this object has a name or alias that matches the given name.
        """
        for alias in self.aliases.all():
            if alias.alias.lower() == name.lower():
                return True
        return self.name.lower() == name.lower()  # pylint: disable=no-member

    def find(self, name: str) -> 'QuerySet["Object"]':
        """
        Find contents by the given name or alias.

        :param name: the name or alias to search for, case-insensitive
        """
        self.can_caller("read", self)
        qs = AccessibleObject.objects.filter(location=self, name__iexact=name)
        aliases = AccessibleObject.objects.filter(location=self, aliases__alias__iexact=name)
        return qs.union(aliases)

    def contains(self, obj: "Object"):
        for item in self.get_contents():
            if item == obj:
                return True
        return False

    def get_ancestors(self) -> Generator["Object", None, None]:
        """
        Get the ancestor tree for this object.
        """
        self.can_caller("read", self)
        # TODO: One day when Django 5.0 works with `django-cte` this can be SQL.
        for parent in self.parents.all():  # pylint: disable=no-member
            yield from parent.get_ancestors()
            yield parent

    def get_descendents(self) -> Generator["Object", None, None]:
        """
        Get the descendent tree for this object.
        """
        self.can_caller("read", self)
        # TODO: One day when Django 5.0 works with `django-cte` this can be SQL.
        for child in self.children.all():
            yield child
            yield from child.get_descendents()

    def get_contents(self) -> Generator["Object", None, None]:
        """
        Get the content tree for this object.
        """
        self.can_caller("read", self)
        # TODO: One day when Django 5.0 works with `django-cte` this can be SQL.
        for item in self.contents.all():
            yield item
            yield from item.get_contents()

    def add_verb(
        self,
        *names: list[str],
        code: str = None,
        owner: "Object" = None,
        repo=None,
        filename: str = None,
        direct_object: str = "none",
        indirect_objects: dict[str, str] = None,
    ):
        """
        Defines a new :class:`.Verb` on the given object.

        :param names: a list of names for the new verb
        :param code: the Python code for the new Verb
        :param owner: the owner of the Verb being created
        :param repo: optional, the Git repo this code is from
        :param filename: optional, the name of the code file within the repo
        :param direct_object: a direct object specifier for the verb
        :param indirect_objects: a list of indirect object specifiers for the verb
        """
        self.can_caller("write", self)
        owner = context.get("caller") or owner or self
        if filename and not code:
            code = bootstrap.get_source(filename, dataset=repo.slug)
        verb = AccessibleVerb.objects.create(
            origin=self,
            owner=owner,
            repo=repo,
            filename=filename,
            code=code,
            direct_object=direct_object,
        )
        if indirect_objects is not None:
            for prep, specifier in indirect_objects.items():
                if prep in ["any", "none"]:
                    p = None
                    prep_specifier = prep
                else:
                    pn = PrepositionName.objects.get(name=prep)
                    p = pn.preposition
                    prep_specifier = "none"
                verb.indirect_objects.add(
                    PrepositionSpecifier.objects.update_or_create(
                        preposition=p, preposition_specifier=prep_specifier, specifier=specifier
                    )[0]
                )
        for name in names:
            verb.names.add(VerbName.objects.create(verb=verb, name=name))
        return verb

    def invoke_verb(self, name, *args, **kwargs):
        """
        Invoke a :class:`.Verb` defined on the given object, traversing the inheritance tree until it's found.

        :param name: the name of the verb
        :param args: positional arguments for the verb
        :param kwargs: keyword arguments for the verb
        """
        qs = self._lookup_verb(name, recurse=True)
        verb = qs[0]
        self.can_caller("execute", verb)
        verb.invoked_name = name
        return verb(*args, **kwargs)

    def has_verb(self, name, recurse=True):
        """
        Check if a particular :class:`.Verb` is defined on this object.

        :param name: the name of the verb
        :param recurse: whether or not to traverse the inheritance tree
        """
        self.can_caller("read", self)
        try:
            self._lookup_verb(name, recurse)
        except AccessibleVerb.DoesNotExist:
            return False
        return True

    def get_verb(self, name, recurse=True, allow_ambiguous=False, return_first=True):
        """
        Retrieve a specific :class:`.Verb` instance defined on this Object.

        :param name: the name of the verb
        :param recurse: whether or not to traverse the inheritance tree
        :param return_first: if True, return the first matching verb, otherwise return all matching verbs
        """
        self.can_caller("read", self)
        verbs = self._lookup_verb(name, recurse, return_first)
        if len(verbs) > 1 and not allow_ambiguous:
            raise exceptions.AmbiguousVerbError(name, verbs)
        for v in verbs:
            v.invoked_name = name
            v.invoked_object = self
        if allow_ambiguous:
            return verbs
        v = verbs[0]
        return v

    def _lookup_verb(self, name, recurse=True, return_first=True):
        found = []
        qs = AccessibleVerb.objects.filter(origin=self, names__name=name)
        if not qs and recurse:
            for ancestor in self.get_ancestors():
                qs = AccessibleVerb.objects.filter(origin=ancestor, names__name=name)
                if qs:
                    if return_first:
                        return qs
                    else:
                        found.extend(qs.all())
        elif qs:
            if return_first:
                return qs
            else:
                found.extend(qs.all())
        if found:
            return found
        else:
            raise AccessibleVerb.DoesNotExist(f"No such verb `{name}`.")

    def set_property(self, name, value, inherited=False, owner=None):
        """
        Defines a new :class:`.Property` on the given object.

        :param names: a list of names for the new Property
        :param value: the value for the new Property
        :param inherited: if True, this property's owner will be reassigned on child instances
        :param owner: the owner of the Property being created
        """
        from .. import moojson

        self.can_caller("write", self)
        owner = context.get("caller") or owner or self
        AccessibleProperty.objects.update_or_create(
            name=name,
            origin=self,
            defaults=dict(
                value=moojson.dumps(value),
                owner=owner,
                type="string",
                inherited=inherited,
            ),
        )

    def get_property(self, name, recurse=True, original=False):
        """
        Retrieve a :class:`.Property` instance defined on this Object.

        :param name: the name of the verb
        :param recurse: whether or not to traverse the inheritance tree
        :param original: if True, return the whole Property object, not just its value
        """
        from .. import moojson

        self.can_caller("read", self)
        qs = AccessibleProperty.objects.filter(origin=self, name=name)
        if not qs and recurse:
            for ancestor in self.get_ancestors():
                qs = AccessibleProperty.objects.filter(origin=ancestor, name=name)
                if qs:
                    break
        if qs:
            return qs[0] if original else moojson.loads(qs[0].value)
        else:
            raise AccessibleProperty.DoesNotExist(f"No such property `{name}`.")

    def has_property(self, name, recurse=True):
        """
        Check if a particular :class:`.Property` is defined on this object.
        """
        self.can_caller("read", self)
        qs = AccessibleProperty.objects.filter(origin=self, name=name)
        if not qs and recurse:
            for ancestor in self.get_ancestors():
                qs = AccessibleProperty.objects.filter(origin=ancestor, name=name)
                if qs:
                    break
        return qs.exists()

    def delete(self, *args, **kwargs):
        try:
            quota = self.owner.get_property("ownership_quota", recurse=False)
            if quota is not None:
                self.owner.set_property("ownership_quota", quota + 1)
        except AccessibleProperty.DoesNotExist:
            pass
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        unsaved = self.pk is None
        if unsaved:
            # there's no permissions yet, so we can't check for `entrust`
            caller = context.get("caller")
            if caller and self.owner != caller:
                raise PermissionError("Can't change owner at creation time.")
        super().save(*args, **kwargs)
        # after saving, new objects need default permissions
        if unsaved:
            utils.apply_default_permissions(self)
        # Recursion Check: note that this leaves a broken object behind unless run in a transaction
        if self.location and self.contains(self.location):
            raise exceptions.RecursiveError(f"{self} already contains {self.location}")
        # ACL Check: to change owner, caller must be allowed to `entrust` on this object
        original_owner = getattr(self, "original_owner", None)
        original_owner = Object.objects.get(pk=original_owner) if original_owner else None
        if original_owner != self.owner and self.owner:
            self.can_caller("entrust", self)
        # ACL Check: to change anything else about the object you at least need `write`
        self.can_caller("write", self)
        # ACL Check: to change the location, caller must be allowed to `move` on this object
        original_location = getattr(self, "original_location", None)
        original_location = Object.objects.get(pk=original_location) if original_location else None
        if original_location != self.location and self.location:
            self.can_caller("move", self)
            # the new location must define an `accept` verb that returns True for this obejct
            if self.location.has_verb("accept"):
                if not self.location.invoke_verb("accept", self):
                    raise PermissionError(f"{self.location} did not accept {self}")
            else:
                raise PermissionError(f"{self.location} did not accept {self}")
            # the optional `exitfunc` Verb will be called asyncronously
            if original_location and original_location.has_verb("exitfunc"):
                invoke(self, verb=original_location.get_verb("exitfunc"))
            # the optional `enterfun` Verb will be called asyncronously
            if self.location and self.location.has_verb("enterfunc"):
                invoke(self, verb=self.location.get_verb("enterfunc"))


# these are the name that django relies on __getattr__ for, there may be others
RESERVED_NAMES = [
    "resolve_expression",
    "get_source_expressions",
    "_prefetched_objects_cache",
    "original_owner",
    "original_location",
]


class AccessibleObject(Object):
    class Meta:
        proxy = True

    # this doesn't work because django uses __getattr__ so heavily
    def __getattr__(self, name):
        if name in RESERVED_NAMES:
            return super().__getattr__(name)  # pylint: disable=no-member
        if self.has_verb(name, recurse=True):
            return self.get_verb(name, recurse=True)
        if self.has_property(name, recurse=True):
            return self.get_property(name, recurse=True)
        raise AttributeError(f"{self} has no attribute `{name}`")

    def owns(self, subject: Object) -> bool:
        """
        Convenience method to check if the `subject` is owned by `self`
        """
        return subject.owner == self

    def is_allowed(self, permission: str, subject, fatal: bool = False) -> bool:
        """
        Check if this object is allowed to perform an action on an object.

        :param permission: the name of the permission to check
        :param subject: the item to check against
        :type subject: Union[Object, Verb, Property]
        :param fatal: if True, raise a :class:`.PermissionError` instead of returning False
        :raises PermissionError: if permission is denied and `fatal` is set to True
        """
        permission = Permission.objects.get(name=permission)
        anything = Permission.objects.get(name="anything")
        rules = Access.objects.filter(
            object=subject if subject.kind == "object" else None,
            verb=subject if subject.kind == "verb" else None,
            property=subject if subject.kind == "property" else None,
            type="accessor",
            accessor=self,
            permission__in=(permission, anything),
        )
        rules = rules.union(
            Access.objects.filter(
                object=subject if subject.kind == "object" else None,
                verb=subject if subject.kind == "verb" else None,
                property=subject if subject.kind == "property" else None,
                type="group",
                group="everyone",
                permission__in=(permission, anything),
            )
        )
        if self.owns(subject):
            rules = rules.union(
                Access.objects.filter(
                    object=subject if subject.kind == "object" else None,
                    verb=subject if subject.kind == "verb" else None,
                    property=subject if subject.kind == "property" else None,
                    type="group",
                    group="owners",
                    permission__in=(permission, anything),
                )
            )
        if Player.objects.filter(avatar=self, wizard=True):
            rules = rules.union(
                Access.objects.filter(
                    object=subject if subject.kind == "object" else None,
                    verb=subject if subject.kind == "verb" else None,
                    property=subject if subject.kind == "property" else None,
                    type="group",
                    group="wizards",
                    permission__in=(permission, anything),
                )
            )
        if rules:
            for rule in rules.order_by("rule", "type"):
                if rule.rule == "deny":
                    if fatal:
                        raise PermissionError(f"{self} is explicitly denied {permission} on {subject}")
                    return False
            return True
        elif fatal:
            raise PermissionError(f"{self} is not allowed {permission} on {subject}")
        else:
            return False


class Relationship(models.Model):
    class Meta:
        unique_together = [["child", "parent"]]

    child = models.ForeignKey(Object, related_name="+", on_delete=models.CASCADE)
    parent = models.ForeignKey(Object, related_name="+", on_delete=models.CASCADE)
    weight = models.IntegerField(default=0)


class Alias(models.Model):
    class Meta:
        verbose_name_plural = "aliases"

    object = models.ForeignKey(Object, related_name="aliases", on_delete=models.CASCADE)
    alias = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.object.can_caller("write", self.object)
        super().save(*args, **kwargs)
