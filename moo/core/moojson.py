"""
Encode/decode MOO JSON
"""

import json
from datetime import date, datetime, time
from typing import Any

_nothing_cache: dict = {}  # site_id -> Object


def _get_nothing() -> Any:
    """
    Return the $nothing sentinel object for the current site.
    Uses a per-site cache; call clear_nothing_cache() in test teardown.
    """
    from .code import ContextManager
    from django.conf import settings

    site = ContextManager.get_site()
    site_id = site.pk if site is not None else getattr(settings, "SITE_ID", 1)

    if site_id not in _nothing_cache:
        from .models.object import Object
        _nothing_cache[site_id] = Object.global_objects.filter(name="nothing", site_id=site_id).first()
    return _nothing_cache[site_id]


def clear_nothing_cache() -> None:
    """Reset the $nothing object cache (call between tests that reset the DB)."""
    _nothing_cache.clear()


def loads(j):
    from .models.object import Object
    from .models.property import Property
    from .models.verb import Verb

    def to_entity(d):
        if len(d) != 1:
            return d
        key = list(d.keys())[0]
        if key == "dt#":
            return datetime.fromisoformat(d[key])
        if key == "d#":
            return date.fromisoformat(d[key])
        if key == "t#":
            return time.fromisoformat(d[key])
        if len(key) >= 2 and key[1] == "#":
            if key[0] == "o":
                try:
                    obj = Object.global_objects.get(pk=int(key[2:]))
                    # If the object belongs to a different universe, treat as nothing
                    nothing = _get_nothing()
                    if nothing is not None and obj.site_id != nothing.site_id:
                        return nothing
                    return obj
                except Object.DoesNotExist:
                    return _get_nothing()
            elif key[0] == "v":
                try:
                    return Verb.objects.get(pk=int(key[2:]))
                except Verb.DoesNotExist:
                    return _get_nothing()
            elif key[0] == "p":
                try:
                    return Property.objects.get(pk=int(key[2:]))
                except Property.DoesNotExist:
                    return _get_nothing()
        return d

    return json.loads(j, object_hook=to_entity)


def dumps(obj):
    from .models.object import Object
    from .models.property import Property
    from .models.verb import Verb

    def from_entity(o):
        if isinstance(o, datetime):
            return {"dt#": o.isoformat()}
        elif isinstance(o, date):
            return {"d#": o.isoformat()}
        elif isinstance(o, time):
            return {"t#": o.isoformat()}
        elif isinstance(o, Object):
            return {"o#%d" % o.pk: o.name}
        elif isinstance(o, Verb):
            return {"v#%d" % o.pk: o.name()}
        elif isinstance(o, Property):
            return {"p#%d" % o.pk: o.name}
        else:
            raise TypeError("Unserializable object {} of type {}".format(obj, type(obj)))

    return json.dumps(obj, default=from_entity)


def filter_nothing(value):
    """
    Remove $nothing sentinel entries from list property values.
    Non-list values are returned unchanged.  Called automatically by
    :meth:`Object.get_property` so callers never see stale object refs.
    """
    nothing = _get_nothing()
    if nothing is None or not isinstance(value, list):
        return value
    nothing_pk = nothing.pk
    return [v for v in value if not (hasattr(v, "pk") and v.pk == nothing_pk)]


def replace_object_refs(j, old_pk, new_obj):
    """
    Return a new JSON string with all ``{"o#<old_pk>": ...}`` references replaced
    by a reference to *new_obj*.  Used at recycle time to substitute ``$nothing``
    for every property that still points at the object being deleted.
    """
    new_ref = {"o#%d" % new_obj.pk: new_obj.name}

    def _replace(data):
        if isinstance(data, dict):
            if len(data) == 1:
                key = list(data.keys())[0]
                if key == "o#%d" % old_pk:
                    return new_ref
            return {k: _replace(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [_replace(item) for item in data]
        return data

    return json.dumps(_replace(json.loads(j)))
