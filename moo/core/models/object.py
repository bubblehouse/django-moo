# -*- coding: utf-8 -*-
"""
The primary Object class
"""

import logging

from django.db import models
from django.db.models import IntegerField, Value
from django.db.models.expressions import F
from django.db.models.query import Q, QuerySet
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django_cte import CTE, with_cte

from moo import bootstrap
from .. import exceptions, invoke, utils
from ..code import ContextManager
from .acl import Access, AccessibleMixin, Permission, _get_permission_id
from .auth import Player
from .property import Property
from .verb import Verb, PrepositionName, PrepositionSpecifier, VerbName

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
    # Assign sequential weights to newly-added parents so lookup priority matches
    # insertion order (last-added parent has highest weight = highest priority).
    existing_before = Relationship.objects.filter(child=child).exclude(parent_id__in=pk_set).count()
    for i, pk in enumerate(sorted(pk_set)):
        Relationship.objects.filter(child=child, parent_id=pk).update(weight=existing_before + i)
    for pk in pk_set:
        parent = model.objects.get(pk=pk)
        # pylint: disable=redefined-builtin
        for property in Property.objects.filter(origin=parent):
            if property.inherit_owner:
                new_owner = property.owner
            else:
                new_owner = child.owner
            Property.objects.update_or_create(
                name=property.name,
                origin=child,
                defaults=dict(
                    owner=new_owner,
                    inherit_owner=property.inherit_owner,
                ),
                create_defaults=dict(
                    owner=new_owner,
                    inherit_owner=property.inherit_owner,
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

        from moo.core import context, lookup
        # in the default DB, all wizards inherit from this Object
        wizard_class = lookup("wizard class")
        # Changes to ManyToMany fields like this are automatically saved
        context.caller.parents.add(wizard_class)
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

    def is_player(self) -> bool:
        """
        Check if this object is a player avatar.
        """
        return Player.objects.filter(avatar=self).exists()

    def is_wizard(self) -> bool:
        """
        Check if this object is a player avatar.
        """
        return Player.objects.filter(avatar=self, wizard=True).exists()

    def is_connected(self) -> bool:
        """
        Check if this object is a player avatar that is currently connected.
        """
        return True

    def is_named(self, name: str) -> bool:
        """
        Check if this object has a name or alias that matches the given name.
        """
        if self.name.lower() == name.lower():  # pylint: disable=no-member
            return True
        if 'aliases' in getattr(self, '_prefetched_objects_cache', {}):
            return any(a.alias.lower() == name.lower() for a in self.aliases.all())
        return self.aliases.filter(alias__iexact=name).exists()

    def find(self, name: str) -> 'QuerySet["Object"]':
        """
        Find contents by the given name or alias.

        :param name: the name or alias to search for, case-insensitive
        """
        self.can_caller("read", self)
        qs = Object.objects.filter(location=self, name__iexact=name)
        aliases = Object.objects.filter(location=self, aliases__alias__iexact=name)
        return qs.union(aliases)

    def contains(self, obj: "Object"):
        return self.get_contents().filter(pk=obj.pk).exists()

    def is_a(self, obj: "Object") -> bool:
        """
        Check if this object is a child of the provided object.

        :param obj: the potential parent object
        :return: True if this object is a child of `obj`
        """
        return self.get_ancestors().filter(pk=obj.pk).exists()

    def _ancestors_cte(self, name="ancestors"):
        """
        Returns a recursive CTE yielding (object_id, depth, path_weight).
        depth=1 is a direct parent. path_weight is the Relationship.weight of
        the depth-1 link that leads to this ancestor (higher = higher priority).
        """
        self_pk = self.pk

        def make_cte(cte):
            return (
                # Base: direct parents at depth=1 with their Relationship weight
                Relationship.objects.filter(child_id=self_pk)
                .values(
                    object_id=F("parent_id"),
                    depth=Value(1, output_field=IntegerField()),
                    path_weight=F("weight"),
                )
                .union(
                    # Recursive: climb further, carrying path_weight from depth-1
                    cte.join(Relationship, child=cte.col.object_id)
                    .values(
                        object_id=F("parent_id"),
                        depth=cte.col.depth + Value(1, output_field=IntegerField()),
                        path_weight=cte.col.path_weight,
                    ),
                    all=True,
                )
            )

        return CTE.recursive(make_cte, name=name)

    def get_ancestors(self) -> QuerySet:
        """
        Get the ancestor tree for this object as a QuerySet ordered shallowest-first.
        Each Object is annotated with ``depth`` (1 = direct parent) and ``path_weight``.
        """
        self.can_caller("read", self)
        ancestors = self._ancestors_cte()
        return with_cte(
            ancestors,
            select=ancestors.join(Object, id=ancestors.col.object_id)
            .annotate(depth=ancestors.col.depth, path_weight=ancestors.col.path_weight)
            .order_by("depth", "-path_weight"),
        )

    def get_descendents(self) -> QuerySet:
        """
        Get the descendent tree for this object as a QuerySet ordered shallowest-first.
        Each Object is annotated with a ``depth`` attribute (1 = direct child).
        """
        self.can_caller("read", self)
        self_pk = self.pk

        def make_cte(cte):
            return (
                Object.objects.filter(pk=self_pk)
                .values(object_id=F("id"), depth=Value(0, output_field=IntegerField()))
                .union(
                    cte.join(Relationship, parent=cte.col.object_id)
                    .values(
                        object_id=F("child_id"),
                        depth=cte.col.depth + Value(1, output_field=IntegerField()),
                    ),
                    all=True,
                )
            )

        cte = CTE.recursive(make_cte)
        return with_cte(
            cte,
            select=cte.join(Object, id=cte.col.object_id)
            .annotate(depth=cte.col.depth)
            .filter(depth__gt=0)
            .order_by("depth"),
        )

    def get_contents(self) -> QuerySet:
        """
        Get the content tree for this object as a QuerySet ordered shallowest-first.
        Each Object is annotated with a ``depth`` attribute (1 = direct content).
        """
        self.can_caller("read", self)
        self_pk = self.pk

        def make_cte(cte):
            return (
                Object.objects.filter(pk=self_pk)
                .values(object_id=F("id"), depth=Value(0, output_field=IntegerField()))
                .union(
                    cte.join(Object, location_id=cte.col.object_id)
                    .values(
                        object_id=F("id"),
                        depth=cte.col.depth + Value(1, output_field=IntegerField()),
                    ),
                    all=True,
                )
            )

        cte = CTE.recursive(make_cte)
        return with_cte(
            cte,
            select=cte.join(Object, id=cte.col.object_id)
            .annotate(depth=cte.col.depth)
            .filter(depth__gt=0)
            .order_by("depth"),
        )

    def add_verb(
        self,
        *names: list[str],
        code: str = None,
        owner: "Object" = None,
        repo=None,
        filename: str = None,
        direct_object: str = "none",
        indirect_objects: dict[str, str] = None,
        replace: bool = False,
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
        owner = ContextManager.get("caller") or owner or self
        if filename and not code:
            code = bootstrap.get_source(filename, dataset=repo.slug)
        verb = None
        if replace and names:
            verb = Verb.objects.filter(origin=self, names__name=names[0]).first()
        if verb is not None:
            verb.owner = owner
            verb.repo = repo
            verb.filename = filename
            verb.code = code
            verb.direct_object = direct_object
            verb.save()
            verb.indirect_objects.clear()
            verb.names.all().delete()
        else:
            verb = Verb.objects.create(
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
            for item in utils.expand_wildcard(name):
                verb.names.add(VerbName.objects.create(verb=verb, name=item))
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
        verb.invoked_object = self
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
        except Verb.DoesNotExist:
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

    def parse_verb(self, parser):
        """
        Check if this parser instance could refer to a verb on this object.
        """
        result = []
        for verb in self._lookup_verb(parser.words[0], recurse=True, return_first=False):
            if verb.direct_object == "this" and parser.dobj != self:
                continue
            if verb.direct_object == "none" and parser.has_dobj_str():
                continue
            if verb.direct_object == "any" and not parser.has_dobj_str():
                continue
            for ispec in verb.indirect_objects.all():
                for prep, values in parser.prepositions.items():
                    if ispec.preposition_specifier == "none":
                        continue
                    if ispec.preposition_specifier == "this" and values[2] != self:
                        continue
                    if ispec.preposition_specifier != "any":
                        if not ispec.preposition.names.filter(name=prep).exists():
                            continue
            # sometimes an object has multiple verbs with the same name after inheritance
            # so we need to check if the verb is already in the list
            if verb not in result:
                result.append(verb)
        if not result:
            return None
        if len(result) == 1:
            return result[0]
        raise exceptions.AmbiguousVerbError(parser.words[0], result)

    def _lookup_verb(self, name, recurse=True, return_first=True):
        # Self always takes priority — check before touching ancestors
        qs = Verb.objects.filter(origin=self, names__name=name).select_related("owner")
        result = list(qs)
        if result:
            return result

        if not recurse:
            raise Verb.DoesNotExist(f"No such verb `{name}`.")

        ancestors = self._ancestors_cte()
        result = list(
            with_cte(
                ancestors,
                select=ancestors.join(Verb, origin_id=ancestors.col.object_id)
                .filter(names__name=name)
                .annotate(
                    ancestor_depth=ancestors.col.depth,
                    path_weight=ancestors.col.path_weight,
                )
                .select_related("owner")
                .order_by("ancestor_depth", "-path_weight"),
            )
        )
        if not result:
            raise Verb.DoesNotExist(f"No such verb `{name}`.")
        if return_first:
            first = result[0]
            return [
                v for v in result
                if v.ancestor_depth == first.ancestor_depth
                and v.path_weight == first.path_weight
            ]
        return result

    def set_property(self, name, value, inherit_owner=False, owner=None):
        """
        Defines a new :class:`.Property` on the given object.

        :param names: a list of names for the new Property
        :param value: the value for the new Property
        :param inherit_owner: if True, this property's owner will be reassigned on child instances
        :param owner: the owner of the Property being created
        """
        from .. import moojson

        self.can_caller("write", self)
        owner = ContextManager.get("caller") or owner or self
        Property.objects.update_or_create(
            name=name,
            origin=self,
            defaults=dict(
                value=moojson.dumps(value),
                owner=owner,
                type="string",
                inherit_owner=inherit_owner,
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
        # Self always takes priority
        prop = Property.objects.filter(origin=self, name=name).first()
        if prop is not None:
            return prop if original else moojson.loads(prop.value)

        if not recurse:
            raise Property.DoesNotExist(f"No such property `{name}`.")

        ancestors = self._ancestors_cte()
        prop = (
            with_cte(
                ancestors,
                select=ancestors.join(Property, origin_id=ancestors.col.object_id)
                .filter(name=name)
                .annotate(
                    ancestor_depth=ancestors.col.depth,
                    path_weight=ancestors.col.path_weight,
                )
                .order_by("ancestor_depth", "-path_weight"),
            )
            .first()
        )
        if prop is None:
            raise Property.DoesNotExist(f"No such property `{name}`.")
        return prop if original else moojson.loads(prop.value)

    def get_property_objects(self, name, prefetch_related=None, select_related=None):
        """
        Like :meth:`get_property`, but when the stored value is a list of Objects,
        returns them via a single bulk ``IN`` query with optional prefetches instead
        of the N individual ``get()`` calls that :func:`moojson.loads` would issue.

        Falls back to :meth:`get_property` for non-list or non-Object values.

        :param name: the property name
        :param prefetch_related: iterable of relation paths to prefetch on the result
        :param select_related: iterable of FK paths to JOIN on the result
        """
        import json
        self.can_caller("read", self)
        # Self always takes priority
        prop = Property.objects.filter(origin=self, name=name).first()
        if prop is None:
            ancestors = self._ancestors_cte()
            prop = with_cte(
                ancestors,
                select=ancestors.join(Property, origin_id=ancestors.col.object_id)
                .filter(name=name)
                .annotate(
                    ancestor_depth=ancestors.col.depth,
                    path_weight=ancestors.col.path_weight,
                )
                .order_by("ancestor_depth", "-path_weight"),
            ).first()
            if prop is None:
                raise Property.DoesNotExist(f"No such property `{name}`.")
        raw = json.loads(prop.value)
        if not isinstance(raw, list):
            from .. import moojson
            return moojson.loads(prop.value)
        ids = [
            int(k[2:])
            for item in raw
            if isinstance(item, dict)
            for k in item
            if len(k) > 2 and k[0] == "o" and k[1] == "#"
        ]
        if not ids:
            return []
        result = Object.objects.filter(id__in=ids)
        if select_related:
            result = result.select_related(*select_related)
        if prefetch_related:
            result = result.prefetch_related(*prefetch_related)
        return list(result)

    def has_property(self, name, recurse=True):
        """
        Check if a particular :class:`.Property` is defined on this object.
        """
        self.can_caller("read", self)
        if Property.objects.filter(origin=self, name=name).exists():
            return True
        if not recurse:
            return False
        ancestors = self._ancestors_cte()
        return with_cte(
            ancestors,
            select=ancestors.join(Property, origin_id=ancestors.col.object_id)
            .filter(name=name),
        ).exists()

    def delete(self, *args, **kwargs):
        if self.has_verb("recycle", recurse=False):
            self.invoke_verb("recycle")
        try:
            quota = self.owner.get_property("ownership_quota", recurse=False)
            if quota is not None:
                self.owner.set_property("ownership_quota", quota + 1)
        except Property.DoesNotExist:
            pass
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        unsaved = self.pk is None
        if unsaved:
            # there's no permissions yet, so we can't check for `entrust`
            caller = ContextManager.get("caller")
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
        original_owner_id = getattr(self, "original_owner", None)
        if original_owner_id != self.owner_id and self.owner_id:
            # Ownership affects the "owners" group match in is_allowed(), so evict any
            # cached permission results for this object before checking entrust.
            cache = ContextManager.get_perm_cache()
            if cache is not None:
                evict = [k for k in cache if k[0] == "perm" and k[3] == self.kind and k[4] == self.pk]
                for k in evict:
                    del cache[k]
            self.can_caller("entrust", self)
        # ACL Check: to change anything else about the object you at least need `write`
        self.can_caller("write", self)
        # ACL Check: to change the location, caller must be allowed to `move` on this object
        original_location_id = getattr(self, "original_location", None)
        if original_location_id != self.location_id and self.location_id:
            self.can_caller("move", self)
            # the new location must define an `accept` verb that returns True for this obejct
            if self.location.has_verb("accept"):
                if not self.location.invoke_verb("accept", self):
                    raise PermissionError(f"{self.location} did not accept {self}")
            else:
                raise PermissionError(f"{self.location} did not accept {self}")
            # the optional `exitfunc` Verb will be called asyncronously
            if original_location_id:
                _prev_location = Object.objects.get(pk=original_location_id)
                if _prev_location.has_verb("exitfunc"):
                    invoke(self, verb=_prev_location.get_verb("exitfunc"))
            # the optional `enterfun` Verb will be called asyncronously
            if self.location and self.location.has_verb("enterfunc"):
                invoke(self, verb=self.location.get_verb("enterfunc"))

    # Django gets upset if this meddles with anything in RESERVED_NAMES
    # but otherwise this seems to work, including in the admin interface
    def __getattr__(self, name):
        if name in RESERVED_NAMES:
            raise AttributeError(name)
        if self.has_verb(name, recurse=True):
            return self.get_verb(name, recurse=True)
        if self.has_property(name, recurse=True):
            return self.get_property(name, recurse=True)
        raise AttributeError(f"{self} has no attribute `{name}`")

    def owns(self, subject) -> bool:
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
        # Per-session cache: only True results are cached so that exact error messages
        # (denied vs. no rules) are preserved on the uncached False path.
        cache = ContextManager.get_perm_cache()
        cache_key = ("perm", self.pk, permission, subject.kind, subject.pk)
        if cache is not None and cache_key in cache:
            return True

        # Resolve permission ids from the process-level cache (Permission table is static).
        perm_id = _get_permission_id(permission)
        try:
            anything_id = _get_permission_id("anything")
            perms = [perm_id, anything_id]
        except Permission.DoesNotExist:
            perms = [perm_id]

        # Build subject filter once
        subject_filter = Q()
        if subject.kind == "object":
            subject_filter = Q(object=subject)
        elif subject.kind == "verb":
            subject_filter = Q(verb=subject)
        elif subject.kind == "property":
            subject_filter = Q(property=subject)

        # Cache wizard status to avoid a repeated Player query on every is_allowed() call.
        wizard_key = ("wizard", self.pk)
        if cache is not None and wizard_key in cache:
            is_wizard = cache[wizard_key]
        else:
            is_wizard = Player.objects.filter(avatar=self, wizard=True).exists()
            if cache is not None:
                cache[wizard_key] = is_wizard

        # Build OR conditions for all matching rules
        query = subject_filter & Q(permission_id__in=perms) & (
            Q(type="accessor", accessor=self) |
            Q(type="group", group="everyone") |
            (Q(type="group", group="owners") if self.owns(subject) else Q()) |
            (Q(type="group", group="wizards") if is_wizard else Q())
        )

        rules = Access.objects.filter(query).order_by("-rule", "type")

        if rules:
            for rule in rules:
                if rule.rule == "deny":
                    if fatal:
                        raise PermissionError(f"{self} is explicitly denied {permission} on {subject}")
                    return False
            if cache is not None:
                cache[cache_key] = True
            return True
        elif fatal:
            raise PermissionError(f"{self} is not allowed {permission} on {subject}")
        else:
            return False


# these are the name that django relies on __getattr__ for, there may be others
RESERVED_NAMES = [
    "resolve_expression",
    "get_source_expressions",
    "_prefetched_objects_cache",
    "original_owner",
    "original_location",
]


class Relationship(models.Model):
    class Meta:
        unique_together = [["child", "parent"]]

    child = models.ForeignKey(Object, related_name="+", on_delete=models.CASCADE)
    parent = models.ForeignKey(Object, related_name="+", on_delete=models.CASCADE)
    weight = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.weight = Relationship.objects.filter(child=self.child).count()
        super().save(*args, **kwargs)


class Alias(models.Model):
    class Meta:
        verbose_name_plural = "aliases"

    object = models.ForeignKey(Object, related_name="aliases", on_delete=models.CASCADE)
    alias = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.object.can_caller("write", self.object)
        super().save(*args, **kwargs)
