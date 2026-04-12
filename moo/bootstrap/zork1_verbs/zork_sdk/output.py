#!moo verb desc global_in --on $zork_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Output helpers for Zork verbs.

desc:      args[0] = object; returns display name string
           (get_property("description") falling back to obj.title())
global_in: args[0] = object, args[1] = location
           Returns True if object is globally visible from location.
"""

from moo.sdk import NoSuchPropertyError

if verb_name == "global_in":
    obj = args[0]
    loc = args[1]
    try:
        scenery = loc.get_property("global_scenery")
    except NoSuchPropertyError:
        scenery = []
    return any(obj.aliases.filter(alias=name).exists() for name in scenery)
else:
    try:
        return args[0].get_property("description")
    except NoSuchPropertyError:
        return args[0].name
