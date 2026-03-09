# -*- coding: utf-8 -*-
"""
Useful global utilities.
"""

import warnings

_VERB_CACHE_KEY = "__set_default_permissions_verb__"


def apply_default_permissions(instance):
    from .code import ContextManager
    from .models import Object
    from .models.verb import Verb

    # Cache the verb in the per-session perm_cache so the DB lookups happen at most
    # once per ContextManager session instead of once per Object/Verb/Property save.
    # Outside a session (e.g. early bootstrap) we still do the full lookup.
    cache = ContextManager.get_perm_cache()
    if cache is not None and _VERB_CACHE_KEY in cache:
        verb = cache[_VERB_CACHE_KEY]
    else:
        system = Object.objects.get(pk=1)
        verb = Verb.objects.filter(origin=system, names__name="set_default_permissions").first()
        if cache is not None and verb is not None:
            cache[_VERB_CACHE_KEY] = verb

    if verb:
        verb.invoked_name = "set_default_permissions"
        verb.invoked_object = verb.origin
        verb(instance)
    else:
        warnings.warn(f"set_default_permissions failed for {instance}: verb not found", category=RuntimeWarning)

def expand_wildcard(name):
    if "*" not in name:
        return [name]
    prefix, suffix = name.split("*", 1)
    result = [prefix]
    for i in range(len(suffix)):
        result.append(prefix + suffix[:i+1])
    return result
