# -*- coding: utf-8 -*-
"""
Object and player query functions.
"""

from typing import Any, Union

from django.db.models import F

from ..core import moojson
from ..core.code import ContextManager as _ContextManager
from ..core.exceptions import (
    QuotaError,
    NoSuchPropertyError,
    NoSuchObjectError,
)
from .context import context


def lookup(x: Union[int, str], return_first: bool = True):
    """
    Lookup an object globally by PK, name, or alias.

    :param x: lookup value
    :param return_first: when True (default), return the first match or raise
        NoSuchObjectError; when False, return a list of all matches (may be empty)
    :return: the result of the lookup, or a list when return_first is False
    :rtype: Object | list[Object]
    :raises NoSuchObjectError: when a result cannot be found and return_first is True
    """
    from django.db.models import Q
    from ..core.models import Object

    if isinstance(x, int):
        return Object.objects.get(pk=x)
    elif isinstance(x, str):
        if x.startswith("$"):
            system = lookup(1)
            return system.get_property(name=x[1:])
        qs = Object.objects.filter(Q(name__iexact=x) | Q(aliases__alias__iexact=x)).distinct()
        if not return_first:
            return list(qs)
        if not qs:
            if context.parser:
                obj = context.parser.get_pronoun_object(x)
                if obj:
                    return obj
            raise NoSuchObjectError(x)
        return qs[0]
    else:
        raise ValueError(f"{x} is not a supported lookup value.")


def connected_players(within=None):
    """
    Return a list of player avatars whose ``last_connected_time`` property was
    updated within the given *within* window (default: 5 minutes).

    The ``last_connected_time`` value is precached into the session-level
    property cache on every returned Object so subsequent ``get_property``
    calls incur no extra queries.

    :param within: recency window; defaults to ``timedelta(minutes=5)``
    :type within: timedelta
    :return: Objects whose avatars have connected recently
    :rtype: list[Object]
    """
    from datetime import datetime, timedelta, timezone
    from ..core.models.property import Property

    if within is None:
        within = timedelta(minutes=5)

    threshold = datetime.now(timezone.utc) - within

    # Single query: restrict to player avatars only and eagerly load the
    # origin Object to avoid per-row SELECT on prop.origin access.
    props = Property.objects.filter(name="last_connected_time", origin__player__isnull=False).select_related("origin")

    pcache = _ContextManager.get_prop_lookup_cache()
    result = []
    for prop in props:
        value = moojson.loads(prop.value)
        if pcache is not None:
            pcache[(prop.origin_id, "last_connected_time", True)] = value
        if value is not None and value >= threshold:
            result.append(prop.origin)

    return result


def prefetch_property(objects: list, name: str) -> None:
    """
    Pre-warm the session property cache for `name` across all objects in 2 DB queries.

    After this call, ``get_property(name)`` on any of these objects hits the in-process
    cache — no further DB or Redis I/O. Handles inheritance via AncestorCache with
    nearest-ancestor-wins semantics (same as ``get_property``).

    Objects whose property resolves to missing are also marked so ``get_property``
    raises ``NoSuchPropertyError`` without a DB hit.
    """
    from ..core.models.property import Property
    from ..core.models.object import AncestorCache, _PROP_MISSING  # noqa: PLC2701

    pcache = _ContextManager.get_prop_lookup_cache()
    if pcache is None or not objects:
        return

    pks = [obj.pk for obj in objects]

    # Pass 1: direct properties (objects that have `name` set on themselves)
    direct = {}
    for prop in Property.objects.filter(origin_id__in=pks, name=name).values("origin_id", "value"):
        direct[prop["origin_id"]] = prop["value"]

    # Pass 2: inherited properties for objects without a direct entry
    no_direct = [pk for pk in pks if pk not in direct]
    inherited: dict[int, Any] = {}
    if no_direct:
        rows = (
            Property.objects.filter(
                origin__ancestor_descendants__descendant_id__in=no_direct,
                name=name,
            )
            .annotate(
                descendant_id=F("origin__ancestor_descendants__descendant_id"),
                depth=F("origin__ancestor_descendants__depth"),
                pw=F("origin__ancestor_descendants__path_weight"),
            )
            .values("descendant_id", "value", "depth", "pw")
        )
        # Take nearest ancestor (min depth, then max path_weight) per descendant
        for row in rows:
            did = row["descendant_id"]
            if (
                did not in inherited
                or row["depth"] < inherited[did]["depth"]
                or (row["depth"] == inherited[did]["depth"] and row["pw"] > inherited[did]["pw"])
            ):
                inherited[did] = row

    # Populate session cache (skip entries already present)
    for pk in pks:
        cache_key = (pk, name, True)
        if cache_key in pcache:
            continue
        if pk in direct:
            pcache[cache_key] = moojson.filter_nothing(moojson.loads(direct[pk]))
        elif pk in inherited:
            pcache[cache_key] = moojson.filter_nothing(moojson.loads(inherited[pk]["value"]))
        else:
            pcache[cache_key] = _PROP_MISSING


def players():
    """
    Return a list of all player avatar Objects.

    :return: Objects that are player avatars
    :rtype: list[Object]
    """
    from ..core.models.auth import Player

    return [p.avatar for p in Player.objects.select_related("avatar").filter(avatar__isnull=False)]


def create(name, *a, **kw):
    """
    Creates and returns a new object whose parents are `parents` and whose owner is as described below.
    Provided `parents` are valid Objects with `derive` permission, otherwise :class:`.PermissionError` is
    raised. After the new object is created, its `initialize` verb, if any, is called with no arguments.

    The owner of the new object is either the programmer (if `owner` is not provided), or the provided owner,
    if the caller has permission to `entrust` the object.

    If the intended owner of the new object has a property named `ownership_quota` and the value of that
    property is an integer, then `create()` treats that value as a quota. If the quota is less than
    or equal to zero, then the quota is considered to be exhausted and `create()` raises :class:`.QuotaError` instead
    of creating an object. Otherwise, the quota is decremented and stored back into the `ownership_quota`
    property as a part of the creation of the new object.

    :param name: canonical name
    :type name: str
    :param owner: owner of the Object being created
    :type owner: Object
    :param location: where to create the Object
    :type location: Object
    :param parents: a list of parents for the Object
    :type parents: list[Object]
    :param obvious: whether the object appears in room contents listings (default False)
    :type obvious: bool
    :return: the new object
    :rtype: Object
    :raises PermissionError: if the caller is not allowed to `derive` from the parent
    :raises QuotaError: if the caller has a quota and it has been exceeded
    """
    from ..core.models.object import Object, Property  # noqa: F401
    from .tasks import invoke  # deferred to avoid circular import

    _SYSTEM_KEY = "__system_object__"
    cache = _ContextManager.get_perm_cache()
    if cache is not None and _SYSTEM_KEY in cache:
        system = cache[_SYSTEM_KEY]
    else:
        system = Object.objects.get(pk=1)
        if cache is not None:
            cache[_SYSTEM_KEY] = system
    default_parents = [system.root_class] if system.has_property("root_class") else []
    if context.caller:
        try:
            quota = context.caller.get_property("ownership_quota", recurse=False)
            if quota > 0:
                context.caller.set_property("ownership_quota", quota - 1)
            else:
                raise QuotaError(f"{context.caller} has run out of quota.")
        except NoSuchPropertyError:
            pass
        if "owner" not in kw:
            kw["owner"] = context.caller
    if "location" not in kw and "owner" in kw:
        kw["location"] = kw["owner"].location
    parents = kw.pop("parents", default_parents)
    obj = Object.objects.create(name=name, *a, **kw)
    if parents:
        obj.parents.add(*parents)
    if obj.has_verb("initialize"):
        invoke(obj.get_verb("initialize"))
    return obj


def owned_objects(player_obj):
    """
    Return a QuerySet of all Objects owned by *player_obj*, ordered by name.

    :param player_obj: the owner Object
    :rtype: QuerySet
    """
    from ..core.models import Object

    return Object.objects.filter(owner=player_obj).order_by("name").select_related("owner")


def owned_objects_by_pks(pk_list):
    """
    Return a QuerySet of Objects with PKs in *pk_list*, ordered by name.

    Used by continuation tasks (e.g. ``audit_batch``) where the target player
    is not in scope but the remaining PK list was passed as ``args[0]``.

    :param pk_list: list of integer Object PKs
    :rtype: QuerySet
    """
    from ..core.models import Object

    return Object.objects.filter(pk__in=pk_list).order_by("name").select_related("owner")
