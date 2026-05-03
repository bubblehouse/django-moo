#!moo verb @audit audit_batch --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
List all objects owned by a player.

Usage:
    @audit              — list your own objects
    @audit <player>     — list another player's objects (wizard only)

For large ownership counts the listing is split across multiple tasks
using time-aware batching. The ``audit_batch`` alias is the continuation
entry point and should not be invoked directly.
"""

from moo.sdk import (
    context,
    lookup,
    owned_objects,
    owned_objects_by_pks,
    task_time_low,
    schedule_continuation,
    NoSuchObjectError,
)

if verb_name == "audit_batch":
    objs = list(owned_objects_by_pks(args[0]))
    for i, obj in enumerate(objs):
        if task_time_low():
            schedule_continuation(objs[i:], this.get_verb("audit_batch"))
            return
        loc = obj.location.name if obj.location else "nowhere"
        context.player.tell(f"  #{obj.id} {obj.name} (in {loc})")
    context.player.tell("Done.")
    return

if context.parser.has_dobj_str():
    if not context.player.is_wizard():
        print("Permission denied.")
        return
    try:
        target = lookup(context.parser.get_dobj_str())
    except NoSuchObjectError:
        print(f"No player named '{context.parser.get_dobj_str()}' found.")
        return
else:
    target = context.player

objs = list(owned_objects(target))
if not objs:
    print(f"{target.name} owns no objects.")
    return

context.player.tell(f"Objects owned by {target.name} ({len(objs)} total):")
for i, obj in enumerate(objs):
    if task_time_low():
        schedule_continuation(objs[i:], this.get_verb("audit_batch"))
        return
    loc = obj.location.name if obj.location else "nowhere"
    context.player.tell(f"  #{obj.id} {obj.name} (in {loc})")
context.player.tell("Done.")
