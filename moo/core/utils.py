# -*- coding: utf-8 -*-
"""
Useful global utilities.
"""

import warnings


def apply_default_permissions(instance):
    from .models import Object
    from .models.verb import Verb
    system = Object.objects.get(pk=1)
    set_default_permissions = Verb.objects.filter(
        origin=system, names__name="set_default_permissions"
    )
    set_default_permissions = set_default_permissions.first()
    if set_default_permissions:
        set_default_permissions.invoked_name = "set_default_permissions"
        set_default_permissions.invoked_object = system
        set_default_permissions(instance)
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
