# -*- coding: utf-8 -*-
"""
The primary Object class
"""

import logging
from typing import Generator

from django.db import models
from django.db.models.query import QuerySet
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .. import bootstrap, exceptions, utils
from ..code import context
from .acl import AccessibleMixin, Access, Permission
from .auth import Player
from .verb import AccessibleVerb, VerbName
from .property import AccessibleProperty

log = logging.getLogger(__name__)

@receiver(m2m_changed)
def relationship_changed(sender, instance, action, model, signal, reverse, pk_set, using, **kwargs):
    child = instance
    if not(sender is Relationship and not reverse):
        return
    elif action in ("pre_add", "pre_remove"):
        child.can_caller('transmute', instance)
        for pk in pk_set:
            parent = model.objects.get(pk=pk)
            parent.can_caller('derive', parent)
        return
    elif action != "post_add":
        return
    for pk in pk_set:
        parent = model.objects.get(pk=pk)
        for property in AccessibleProperty.objects.filter(origin=parent, inherited=True):  # pylint: disable=redefined-builtin
            AccessibleProperty.objects.update_or_create(
                name = property.name,
                origin = child,
                defaults = dict(
                    owner = child.owner,
                    inherited = property.inherited,
                ),
                create_defaults = dict(
                    owner = child.owner,
                    inherited = property.inherited,
                    value = property.value,
                    type = property.type,
                )
            )

class Object(models.Model, AccessibleMixin):
    #: The canonical name of the object
    name = models.CharField(max_length=255)
    #: If True, this object is the only object with this name
    unique_name = models.BooleanField(default=False)
    #: This object should be obvious among a group. The meaning of this value is database-dependent.
    obvious = models.BooleanField(default=True)
    #: The owner of this object. Changes require `entrust` permission.
    owner = models.ForeignKey('self', related_name='+', blank=True, null=True, on_delete=models.SET_NULL,)
    #: The parents of this object. Changes require `derive` and `transmute` permissions, respectively
    parents = models.ManyToManyField('self', related_name='children', blank=True, symmetrical=False, through='Relationship')
    location = models.ForeignKey('self', related_name='contents', blank=True, null=True, on_delete=models.SET_NULL)
    """
    [`TODO <https://gitlab.com/bubblehouse/django-moo/-/issues/12>`_]
    The location of this object. When changing, this kicks off some other verbs:

    If `where` is the new object, then the verb-call `where.accept(self)` is performed before any movement takes place.
    If the verb returns a false value and the programmer is not a wizard, then `where` is considered to have refused entrance
    to `self` and raises :class:`.PermissionError`. If `where` does not define an `accept` verb, then it is treated as if
    it defined one that always returned false.

    If moving `what` into `self` would create a loop in the containment hierarchy (i.e., what would contain itself, even
    indirectly), then :class:`.RecursiveError` is raised instead.

    Let `old-where` be the location of `self` before it was moved. If `old-where` is a valid object, then the verb-call
    `old-where:exitfunc(self)` is performed and its result is ignored; it is not an error if `old-where` does not define
    a verb named `exitfunc`.

    Finally, if `where` is still the location of `self`, then the verb-call `where:enterfunc(self)` is performed and its
    result is ignored; again, it is not an error if `where` does not define a verb named `enterfunc`.
    """

    def __str__(self):
        return "#%s (%s)" % (self.id, self.name)

    @property
    def kind(self):
        return 'object'

    def find(self, name: str) -> 'QuerySet["Object"]':
        """
        Find contents by the given name or alias.

        :param name: the name or alias to search for, case-insensitive
        """
        self.can_caller('read', self)
        qs = AccessibleObject.objects.filter(location=self, name__iexact=name)
        aliases = AccessibleObject.objects.filter(location=self, aliases__alias__iexact=name)
        return qs.union(aliases)

    def get_ancestors(self) -> Generator["Object", None, None]:
        """
        Get the ancestor tree for this object.
        """
        self.can_caller('read', self)
        # TODO: One day when Django 5.0 works with `django-cte` this can be SQL.
        for parent in self.parents.all():
            yield parent
            yield from parent.get_ancestors()

    def get_descendents(self) -> Generator["Object", None, None]:
        """
        Get the descendent tree for this object.
        """
        self.can_caller('read', self)
        # TODO: One day when Django 5.0 works with `django-cte` this can be SQL.
        for child in self.children.all():
            yield child
            yield from child.get_descendents()

    def add_verb(self, *names:list[str], code:str=None, owner:"Object"=None, repo=None, filename:str=None, ability:bool=False, method:bool=False):
        """
        Defines a new :class:`.Verb` on the given object.

        :param names: a list of names for the new verb
        :param code: the Python code for the new Verb
        :param owner: the owner of the Verb being created
        :param repo: optional, the Git repo this code is from
        :param filename: optional, the name of the code file within the repo
        :param ability: if True, this verb can only be used by the object it is defined on
        :param method: if True, this verb can be invoked by other verbs
        """
        self.can_caller('write', self)
        owner = context.get('caller') or owner or self
        if filename:
            code = bootstrap.get_source(filename, dataset=repo.slug)
        verb = AccessibleVerb.objects.create(
            method = method,
            ability = ability,
            origin = self,
            owner = owner,
            repo = repo,
            filename = filename,
            code = code
        )
        for name in names:
            verb.names.add(VerbName.objects.create(
                verb=verb,
                name=name
            ))
        return verb

    def invoke_verb(self, name, *args, **kwargs):
        """
        Invoke a :class:`.Verb` defined on the given object, traversing the inheritance tree until it's found.

        :param name: the name of the verb
        :param args: positional arguments for the verb
        :param kwargs: keyword arguments for the verb
        """
        qs = self._lookup_verb(name, recurse=True)
        self.can_caller('execute', qs[0])
        return qs[0](*args, **kwargs)

    def has_verb(self, name, recurse=True):
        """
        Check if a particular :class:`.Verb` is defined on this object.

        :param name: the name of the verb
        :param recurse: whether or not to traverse the inheritance tree
        """
        self.can_caller('read', self)
        try:
            self._lookup_verb(name, recurse)
        except AccessibleVerb.DoesNotExist:
            return False
        return True

    def get_verb(self, name, recurse=True):
        """
        Retrieve a specific :class:`.Verb` instance defined on this Object.

        :param name: the name of the verb
        :param recurse: whether or not to traverse the inheritance tree
        """
        self.can_caller('read', self)
        qs = self._lookup_verb(name, recurse)
        if len(qs) > 1:
            raise exceptions.AmbiguousVerbError(name, list(qs.all()))
        return qs[0]

    def _lookup_verb(self, name, recurse=True):
        qs = AccessibleVerb.objects.filter(origin=self, names__name=name)
        if not qs and recurse:
            for ancestor in self.get_ancestors():
                qs = AccessibleVerb.objects.filter(origin=ancestor, names__name=name)
                if qs:
                    break
        if qs:
            return qs
        else:
            raise AccessibleVerb.DoesNotExist(f"No such verb `{name}`.")

    def set_property(self, name, value, inherited=False, owner=None):
        """
        Defines a new :class:`.Property` on the given object.

        :param names: a list of names for the new Property
        :param value: the value code for the new Property
        :param inherited: if True, this property's owner will be reassigned on child instances
        :param owner: the owner of the Property being created
        """
        self.can_caller('write', self)
        owner = context.get('caller') or owner or self
        AccessibleProperty.objects.update_or_create(
            name = name,
            origin = self,
            defaults = dict(
                value = value,
                owner = owner,
                type = "string",
                inherited = inherited,
            )
        )

    def get_property(self, name, recurse=True, original=False):
        """
        Retrieve a :class:`.Property` instance defined on this Object.

        :param name: the name of the verb
        :param recurse: whether or not to traverse the inheritance tree
        :param original: if True, return the whole Property object, not just its value
        """
        self.can_caller('read', self)
        qs = AccessibleProperty.objects.filter(origin=self, name=name)
        if not qs and recurse:
            for ancestor in self.get_ancestors():
                qs = AccessibleProperty.objects.filter(origin=ancestor, name=name)
                if qs:
                    break
        if qs:
            return qs[0] if original else qs[0].value
        else:
            raise AccessibleProperty.DoesNotExist(f"No such property `{name}`.")

    def save(self, *args, **kwargs):
        needs_default_permissions = self.pk is None
        super().save(*args, **kwargs)
        if not needs_default_permissions:
            return
        utils.apply_default_permissions(self)

class AccessibleObject(Object):
    class Meta:
        proxy = True

    def owns(self, subject):
        return subject.owner == self

    def is_allowed(self, permission, subject, fatal=False):
        permission = Permission.objects.get(name=permission)
        anything = Permission.objects.get(name='anything')
        rules = Access.objects.filter(
            object = subject if subject.kind == 'object' else None,
            verb = subject if subject.kind == 'verb' else None,
            property = subject if subject.kind == 'property' else None,
            type = 'accessor',
            accessor = self,
            permission__in = (permission, anything)
        )
        rules = rules.union(Access.objects.filter(
            object = subject if subject.kind == 'object' else None,
            verb = subject if subject.kind == 'verb' else None,
            property = subject if subject.kind == 'property' else None,
            type = 'group',
            group = 'everyone',
            permission__in = (permission, anything)
        ))
        if self.owns(subject):
            rules = rules.union(Access.objects.filter(
                object = subject if subject.kind == 'object' else None,
                verb = subject if subject.kind == 'verb' else None,
                property = subject if subject.kind == 'property' else None,
                type = 'group',
                group = 'owners',
                permission__in = (permission, anything)
            ))
        if Player.objects.filter(avatar=self, wizard=True):
            rules = rules.union(Access.objects.filter(
                object = subject if subject.kind == 'object' else None,
                verb = subject if subject.kind == 'verb' else None,
                property = subject if subject.kind == 'property' else None,
                type = 'group',
                group = 'wizards',
                permission__in = (permission, anything)
            ))
        if rules:
            for rule in rules.order_by("rule", "type"):
                if rule.rule == 'deny':
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
        unique_together = [['child', 'parent']]

    child = models.ForeignKey(Object, related_name='+', on_delete=models.CASCADE)
    parent = models.ForeignKey(Object, related_name='+', on_delete=models.CASCADE)
    weight = models.IntegerField(default=0)

class Alias(models.Model):
    class Meta:
        verbose_name_plural = 'aliases'

    object = models.ForeignKey(Object, related_name='aliases', on_delete=models.CASCADE)
    alias = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.object.can_caller('write', self.object)
        super().save(*args, **kwargs)
