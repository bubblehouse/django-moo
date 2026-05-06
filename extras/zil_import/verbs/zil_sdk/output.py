#!moo verb desc global_in --on "Zork Root"
# pylint: disable=return-outside-function,undefined-variable
"""
Output / scope helpers for Zork verbs.

desc:      no args; returns ``this.get_property("description")`` falling
           back to ``this.name``.  Translated routines call as
           ``obj.desc()``.
global_in: args[0] = location; True if ``this`` appears in the location's
           ``global_scenery`` list.  Called as ``obj.global_in(loc)``.
"""

from moo.sdk import NoSuchPropertyError

if verb_name == "global_in":
    loc = args[0]
    try:
        scenery = loc.get_property("global_scenery")
    except NoSuchPropertyError:
        scenery = []
    if not scenery:
        return False
    # Single query across the whole scenery list rather than N exists() calls.
    return this.aliases.filter(alias__in=scenery).exists()
else:
    try:
        return this.get_property("description")
    except NoSuchPropertyError:
        return this.name
