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
from django.conf import settings
from django.core.cache import cache
from django_cte import CTE, with_cte

from moo import bootstrap
from .. import exceptions, invoke, utils
from ..exceptions import NoSuchVerbError, NoSuchPropertyError
from ..code import ContextManager
from .acl import Access, AccessibleMixin, Permission, _get_permission_id
from .auth import Player
from .property import Property
from .verb import Verb, PrepositionName, PrepositionSpecifier, VerbName

log = logging.getLogger(__name__)

# Sentinel used by the per-session property lookup cache to distinguish
# "cached miss" (property does not exist) from "not yet cached" (None).
_PROP_MISSING = object()

# Sentinel stored in the cache backend to record a confirmed property miss
# (no such property on this object or any ancestor). Must not be a valid moojson value.
_CACHE_PROP_MISSING = "__moo:prop:missing__"

# Sentinel stored in the cache backend to record a confirmed verb miss.
_CACHE_VERB_MISSING = "__moo:verb:missing__"

# Sentinel returned by cache.get() when a key is absent (never stored in the cache).
_CACHE_MISS = object()


def _make_ancestors_cte(self_pk, name="ancestors"):
    """
    Returns a recursive CTE yielding (object_id, depth, path_weight) for the given PK.
    depth=1 is a direct parent. path_weight is the Relationship.weight of the depth-1 link.
    Factored out so rebuild helpers can use it without an Object instance.
    """

    def make_cte(cte):
        return (
            Relationship.objects.filter(child_id=self_pk)
            .values(
                object_id=F("parent_id"),
                depth=Value(1, output_field=IntegerField()),
                path_weight=F("weight"),
            )
            .union(
                cte.join(Relationship, child=cte.col.object_id).values(
                    object_id=F("parent_id"),
                    depth=cte.col.depth + Value(1, output_field=IntegerField()),
                    path_weight=cte.col.path_weight,
                ),
                all=True,
            )
        )

    return CTE.recursive(make_cte, name=name)


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
    elif action == "post_remove":
        _rebuild_ancestor_cache_for(child)
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
        parent_props = list(Property.objects.filter(origin=parent))
        if not parent_props:
            continue
        # Identify which properties already exist on the child so we don't
        # overwrite their values — only update owner/inherit_owner.
        existing = {p.name: p for p in Property.objects.filter(origin=child, name__in=[p.name for p in parent_props])}
        to_create = []
        to_update = []
        for prop in parent_props:
            new_owner = prop.owner if prop.inherit_owner else child.owner
            if prop.name in existing:
                ep = existing[prop.name]
                ep.owner = new_owner
                ep.inherit_owner = prop.inherit_owner
                to_update.append(ep)
            else:
                to_create.append(
                    Property(
                        name=prop.name,
                        origin=child,
                        owner=new_owner,
                        inherit_owner=prop.inherit_owner,
                        value=prop.value,
                        type=prop.type,
                    )
                )
        if to_create:
            # bulk_create returns objects with PKs populated; apply ACL in one shot.
            created = Property.objects.bulk_create(to_create)
            utils.apply_default_permissions_bulk(created)
        if to_update:
            Property.objects.bulk_update(to_update, ["owner", "inherit_owner"])
    _rebuild_ancestor_cache_for(child)


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

    _original_owner = None
    _original_location = None

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._original_owner = values[field_names.index("owner_id")]  # pylint: disable=protected-access
        instance._original_location = values[field_names.index("location_id")]  # pylint: disable=protected-access
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
        Check if this object is a wizard player avatar.
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
        if "aliases" in getattr(self, "_prefetched_objects_cache", {}):
            return any(a.alias.lower() == name.lower() for a in self.aliases.all())
        return self.aliases.filter(alias__iexact=name).exists()

    def find(self, name: str) -> 'QuerySet["Object"]':
        """
        Find contents by the given name or alias.

        :param name: the name or alias to search for, case-insensitive
        """
        self.can_caller("read", self)
        return (
            Object.objects.filter(location=self)
            .filter(Q(name__iexact=name) | Q(aliases__alias__iexact=name))
            .distinct()
        )

    def contains(self, obj: "Object") -> bool:
        """
        Check if this object contains the given object anywhere in its content tree.

        :param obj: the object to search for
        :return: True if `obj` is found in the content tree of this object
        """
        return self.get_contents().filter(pk=obj.pk).exists()

    def is_a(self, obj: "Object") -> bool:
        """
        Check if this object is a child of the provided object.

        :param obj: the potential parent object
        :return: True if this object is a child of `obj`
        """
        return AncestorCache.objects.filter(descendant=self, ancestor=obj).exists()

    def _ancestors_cte(self, name="ancestors"):
        """
        Returns a recursive CTE yielding (object_id, depth, path_weight).
        depth=1 is a direct parent. path_weight is the Relationship.weight of
        the depth-1 link that leads to this ancestor (higher = higher priority).
        """
        return _make_ancestors_cte(self.pk, name)

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
                    cte.join(Relationship, parent=cte.col.object_id).values(
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
                    cte.join(Object, location_id=cte.col.object_id).values(
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
        # Evict cached verb lookups for all names on this object so subsequent
        # dispatches in the same session see the new verb.
        vcache = ContextManager.get_verb_lookup_cache()
        if vcache is not None:
            for name in names:
                for item in utils.expand_wildcard(name):
                    for recurse_flag in (True, False):
                        for return_first_flag in (True, False):
                            vcache.pop((self.pk, item, recurse_flag, return_first_flag), None)
        # Evict cross-session Redis verb cache entries for this object.
        if getattr(settings, "MOO_ATTRIB_CACHE_TTL", 120) > 0:
            for name in names:
                for item in utils.expand_wildcard(name):
                    for recurse_flag in (True, False):
                        for return_first_flag in (True, False):
                            cache.delete(f"moo:verb:{self.pk}:{item}:{int(recurse_flag)}:{int(return_first_flag)}")
        return verb

    def add_alias(self, alias: str):
        """
        Add an alias to this object if it does not already exist.

        :param alias: the alias string to add
        """
        if not self.aliases.filter(alias=alias).exists():
            Alias(object=self, alias=alias).save()

    def add_parent(self, parent: "Object"):
        """
        Add a parent to this object's inheritance chain.

        :param parent: the parent Object to add
        :raises PermissionError: if the caller does not have derive permission on the parent
        """
        self.can_caller("write", self)
        parent.can_caller("derive", parent)
        self.parents.add(parent)

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
        verb._invoked_name = name  # pylint: disable=protected-access
        verb._invoked_object = self  # pylint: disable=protected-access
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
        except NoSuchVerbError:
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
            v._invoked_name = name  # pylint: disable=protected-access
            v._invoked_object = self  # pylint: disable=protected-access
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
        vcache = ContextManager.get_verb_lookup_cache()
        cache_key = (self.pk, name, recurse, return_first)
        if vcache is not None and cache_key in vcache:
            cached = vcache[cache_key]
            if cached is None:
                raise NoSuchVerbError(name)
            return cached

        # Cross-session Redis cache — stores comma-separated verb PKs to avoid the
        # expensive AncestorCache JOIN on repeated lookups across requests.
        # Bypassed when MOO_ATTRIB_CACHE_TTL=0 (e.g. tests).
        _cache_ttl = getattr(settings, "MOO_ATTRIB_CACHE_TTL", 120)
        redis_key = None if _cache_ttl == 0 else f"moo:verb:{self.pk}:{name}:{int(recurse)}:{int(return_first)}"
        if redis_key is not None:
            raw = cache.get(redis_key, _CACHE_MISS)
            if raw is not _CACHE_MISS:
                if raw == _CACHE_VERB_MISSING:
                    if vcache is not None:
                        vcache[cache_key] = None
                    raise NoSuchVerbError(name)
                pks = [int(p) for p in raw.split(",")]
                result = list(
                    Verb.objects.filter(pk__in=pks)
                    .select_related("owner")
                    .prefetch_related("indirect_objects__preposition__names")
                )
                if vcache is not None:
                    vcache[cache_key] = result
                return result

        # Self always takes priority — check before touching ancestors
        qs = (
            Verb.objects.filter(origin=self, names__name=name)
            .select_related("owner")
            .prefetch_related("indirect_objects__preposition__names")
        )
        result = list(qs)
        if result:
            if vcache is not None:
                vcache[cache_key] = result
            if redis_key is not None:
                cache.set(redis_key, ",".join(str(v.pk) for v in result), timeout=_cache_ttl)
            return result

        if not recurse:
            if vcache is not None:
                vcache[cache_key] = None
            if redis_key is not None:
                cache.set(redis_key, _CACHE_VERB_MISSING, timeout=_cache_ttl)
            raise NoSuchVerbError(name)

        result = list(
            Verb.objects.filter(
                origin__ancestor_descendants__descendant=self,
                names__name=name,
            )
            .annotate(
                ancestor_depth=F("origin__ancestor_descendants__depth"),
                path_weight=F("origin__ancestor_descendants__path_weight"),
            )
            .order_by("ancestor_depth", "-path_weight")
            .select_related("owner")
            .prefetch_related("indirect_objects__preposition__names")
        )
        if not result:
            if vcache is not None:
                vcache[cache_key] = None
            if redis_key is not None:
                cache.set(redis_key, _CACHE_VERB_MISSING, timeout=_cache_ttl)
            raise NoSuchVerbError(name)
        if return_first:
            first = result[0]
            result = [
                v for v in result if v.ancestor_depth == first.ancestor_depth and v.path_weight == first.path_weight
            ]
        if vcache is not None:
            vcache[cache_key] = result
        if redis_key is not None:
            cache.set(redis_key, ",".join(str(v.pk) for v in result), timeout=_cache_ttl)
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
        # Evict cached property values for this object so subsequent reads in
        # the same session see the freshly written value.
        pcache = ContextManager.get_prop_lookup_cache()
        if pcache is not None:
            for recurse_flag in (True, False):
                pcache.pop((self.pk, name, recurse_flag), None)
        # Evict the cross-session cache for this object's property.
        # Descendant caches are intentionally not invalidated here — they will
        # expire naturally within MOO_ATTRIB_CACHE_TTL, which is acceptable for gameplay.
        if getattr(settings, "MOO_ATTRIB_CACHE_TTL", 120) > 0:
            for recurse_flag in (True, False):
                cache.delete(f"moo:prop:{self.pk}:{name}:{int(recurse_flag)}")

    def get_property(self, name, recurse=True, original=False):
        """
        Retrieve a :class:`.Property` instance defined on this Object.

        :param name: the name of the verb
        :param recurse: whether or not to traverse the inheritance tree
        :param original: if True, return the whole Property object, not just its value
        """
        from .. import moojson

        self.can_caller("read", self)

        # Session-level cache for non-original (value) lookups only — Property
        # objects carry ORM state that should not be shared across call frames.
        pcache = None if original else ContextManager.get_prop_lookup_cache()
        session_key = (self.pk, name, recurse) if pcache is not None else None
        if session_key is not None and session_key in pcache:
            cached = pcache[session_key]
            if cached is _PROP_MISSING:
                raise NoSuchPropertyError(name)
            return cached

        # Cross-session cache — stores raw moojson text to avoid serialization
        # issues with Object references.  _CACHE_PROP_MISSING marks confirmed misses.
        # Bypassed for original=True (returns a Property ORM object, not cacheable).
        # Bypassed when MOO_ATTRIB_CACHE_TTL=0 (e.g. tests, where the in-process cache
        # does not reset between test cases and would poison subsequent tests).
        _cache_ttl = getattr(settings, "MOO_ATTRIB_CACHE_TTL", 120)
        cache_key = None if (original or _cache_ttl == 0) else f"moo:prop:{self.pk}:{name}:{int(recurse)}"
        if cache_key is not None:
            raw = cache.get(cache_key, _CACHE_MISS)
            if raw is not _CACHE_MISS:
                if raw == _CACHE_PROP_MISSING:
                    if session_key is not None:
                        pcache[session_key] = _PROP_MISSING
                    raise NoSuchPropertyError(name)
                value = moojson.loads(raw)
                if session_key is not None:
                    pcache[session_key] = value
                return value

        # Self always takes priority
        prop = Property.objects.filter(origin=self, name=name).first()
        if prop is not None:
            value = prop if original else moojson.loads(prop.value)
            if session_key is not None:
                pcache[session_key] = value
            if cache_key is not None:
                cache.set(cache_key, prop.value if prop.value is not None else "null", timeout=_cache_ttl)
            return value

        if not recurse:
            if session_key is not None:
                pcache[session_key] = _PROP_MISSING
            if cache_key is not None:
                cache.set(cache_key, _CACHE_PROP_MISSING, timeout=_cache_ttl)
            raise NoSuchPropertyError(name)

        prop = (
            Property.objects.filter(
                origin__ancestor_descendants__descendant=self,
                name=name,
            )
            .annotate(
                ancestor_depth=F("origin__ancestor_descendants__depth"),
                path_weight=F("origin__ancestor_descendants__path_weight"),
            )
            .order_by("ancestor_depth", "-path_weight")
            .first()
        )
        if prop is None:
            if session_key is not None:
                pcache[session_key] = _PROP_MISSING
            if cache_key is not None:
                cache.set(cache_key, _CACHE_PROP_MISSING, timeout=_cache_ttl)
            raise NoSuchPropertyError(name)
        value = prop if original else moojson.loads(prop.value)
        if session_key is not None:
            pcache[session_key] = value
        if cache_key is not None:
            cache.set(cache_key, prop.value if prop.value is not None else "null", timeout=_cache_ttl)
        return value

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
            prop = (
                Property.objects.filter(
                    origin__ancestor_descendants__descendant=self,
                    name=name,
                )
                .annotate(
                    ancestor_depth=F("origin__ancestor_descendants__depth"),
                    path_weight=F("origin__ancestor_descendants__path_weight"),
                )
                .order_by("ancestor_depth", "-path_weight")
                .first()
            )
            if prop is None:
                raise NoSuchPropertyError(name)
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
        return Property.objects.filter(
            origin__ancestor_descendants__descendant=self,
            name=name,
        ).exists()

    def delete(self, *args, **kwargs):
        self.can_caller("write", self)
        if self.has_verb("recycle", recurse=False):
            self.invoke_verb("recycle")
        try:
            quota = self.owner.get_property("ownership_quota", recurse=False)
            if quota is not None:
                self.owner.set_property("ownership_quota", quota + 1)
        except NoSuchPropertyError:
            pass
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        unsaved = self.pk is None
        if unsaved:
            # there's no permissions yet, so we can't check for `entrust`
            caller = ContextManager.get("caller")
            if caller and self.owner != caller:
                raise PermissionError("Can't change owner at creation time.")
        # Recursion Check: must run BEFORE super().save() so the loop never reaches the DB;
        # a new object (unsaved) cannot yet contain anything, so skip it there.
        if not unsaved and self.location and self.contains(self.location):
            raise exceptions.RecursiveError(f"{self} already contains {self.location}")
        super().save(*args, **kwargs)
        # after saving, new objects need default permissions
        if unsaved:
            utils.apply_default_permissions(self)
        # ACL Check: to change owner, caller must be allowed to `entrust` on this object
        original_owner_id = self._original_owner
        if original_owner_id != self.owner_id and self.owner_id:
            # Ownership affects the "owners" group match in is_allowed(), so evict any
            # cached permission results for this object before checking entrust.
            perm_cache = ContextManager.get_perm_cache()
            if perm_cache is not None:
                evict = [k for k in perm_cache if k[0] == "perm" and k[3] == self.kind and k[4] == self.pk]
                for k in evict:
                    del perm_cache[k]
            self.can_caller("entrust", self)
        # ACL Check: to change anything else about the object you at least need `write`
        self.can_caller("write", self)
        # ACL Check: to change the location, caller must be allowed to `move` on this object
        original_location_id = self._original_location
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
            # the optional `enterfunc` Verb will be called asyncronously
            if self.location and self.location.has_verb("enterfunc"):
                invoke(self, verb=self.location.get_verb("enterfunc"))
            self._original_location = self.location_id

    # Django gets upset if this meddles with anything in RESERVED_NAMES
    # but otherwise this seems to work, including in the admin interface
    def __getattr__(self, name):
        if name in RESERVED_NAMES:
            raise AttributeError(name)
        try:
            return self.get_verb(name, recurse=True)
        except NoSuchVerbError:
            pass
        try:
            return self.get_property(name, recurse=True)
        except NoSuchPropertyError:
            pass
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
        perm_cache = ContextManager.get_perm_cache()
        cache_key = ("perm", self.pk, permission, subject.kind, subject.pk)
        if perm_cache is not None and cache_key in perm_cache:
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
        if perm_cache is not None and wizard_key in perm_cache:
            is_wizard = perm_cache[wizard_key]
        else:
            is_wizard = Player.objects.filter(avatar=self, wizard=True).exists()
            if perm_cache is not None:
                perm_cache[wizard_key] = is_wizard

        # Build OR conditions for all matching rules
        query = (
            subject_filter
            & Q(permission_id__in=perms)
            & (
                Q(type="accessor", accessor=self)
                | Q(type="group", group="everyone")
                | (Q(type="group", group="owners") if self.owns(subject) else Q())
                | (Q(type="group", group="wizards") if is_wizard else Q())
            )
        )

        rules = Access.objects.filter(query).order_by("-rule", "type")

        if rules:
            for rule in rules:
                if rule.rule == "deny":
                    if fatal:
                        raise exceptions.AccessError(self, permission, subject)
                    return False
            if perm_cache is not None:
                perm_cache[cache_key] = True
            return True
        elif fatal:
            raise exceptions.AccessError(self, permission, subject)
        else:
            return False


# these are the name that django relies on __getattr__ for, there may be others
RESERVED_NAMES = [
    "resolve_expression",
    "get_source_expressions",
    "_prefetched_objects_cache",
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

    def delete(self, *args, **kwargs):
        self.object.can_caller("write", self.object)
        super().delete(*args, **kwargs)


class AncestorCache(models.Model):
    """
    Denormalized flat table of ancestor relationships for fast indexed JOINs.
    Replaces recursive CTE usage in hot-path verb and property lookups.
    Maintained by the relationship_changed() signal on parents.add/remove.
    """

    class Meta:
        unique_together = [["descendant", "ancestor"]]
        indexes = [
            models.Index(
                fields=["descendant", "depth", "path_weight"],
                name="ac_desc_depth_weight_idx",
            ),
            models.Index(fields=["ancestor"], name="ancestorcache_ancestor_idx"),
        ]

    descendant = models.ForeignKey(Object, related_name="ancestor_cache", on_delete=models.CASCADE)
    ancestor = models.ForeignKey(Object, related_name="ancestor_descendants", on_delete=models.CASCADE)
    depth = models.IntegerField()
    path_weight = models.IntegerField()


def _collect_descendants_pks(root_pk):
    """
    Returns the set of all descendant PKs for the given root_pk using direct
    Relationship queries — no permission checks, safe to call from signal handlers.
    """
    result = set()
    queue = list(Relationship.objects.filter(parent_id=root_pk).values_list("child_id", flat=True))
    while queue:
        pk = queue.pop()
        if pk not in result:
            result.add(pk)
            queue.extend(Relationship.objects.filter(parent_id=pk).values_list("child_id", flat=True))
    return result


def _rebuild_ancestor_cache_for(obj):
    """
    Rebuild the AncestorCache rows for `obj` and all its descendants.
    Called after any parents.add() or parents.remove() signal.
    """
    affected_pks = _collect_descendants_pks(obj.pk)
    affected_pks.add(obj.pk)

    AncestorCache.objects.filter(descendant_id__in=affected_pks).delete()

    rows = []
    for pk in affected_pks:
        ancestors_cte = _make_ancestors_cte(pk)
        # Deduplicate: for each ancestor keep only the shallowest path
        # (min depth, and max path_weight among those at min depth).
        seen = {}
        for row in with_cte(
            ancestors_cte,
            select=ancestors_cte.join(Object, id=ancestors_cte.col.object_id)
            .annotate(depth=ancestors_cte.col.depth, path_weight=ancestors_cte.col.path_weight)
            .order_by("depth", "-path_weight"),
        ).values("id", "depth", "path_weight"):
            if row["id"] not in seen:
                seen[row["id"]] = row
        for row in seen.values():
            rows.append(
                AncestorCache(
                    descendant_id=pk,
                    ancestor_id=row["id"],
                    depth=row["depth"],
                    path_weight=row["path_weight"],
                )
            )

    if rows:
        AncestorCache.objects.bulk_create(rows, ignore_conflicts=True)
