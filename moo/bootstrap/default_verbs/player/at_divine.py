#!moo verb @divine --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Consult the aether for random world objects by subject.

Usage:
    @divine location               — surface random rooms from the wider world
    @divine child of $thing        — surface three random descendants of a class
    @divine location of <object>   — find the enclosing room of an object

The class reference for `child of` accepts `$name` (system property), `#N`,
or a bare world-object name. The target for `location of` accepts the same
forms. The location walk climbs the container tree until it finds a `$room`
subclass, so objects buried inside containers still resolve to the room that
contains them.

Note: `of` is not a parser preposition (it conflicts with object names like
"scrap of paper"), so this verb parses the `of` split directly from the raw
dobj string.
"""

import random
from moo.sdk import context, lookup, NoSuchObjectError, NoSuchPropertyError

raw = (context.parser.get_dobj_str() or "").strip()
if not raw:
    print("Divine what? Try: @divine location, @divine child of $thing, @divine location of <object>")
    return

system = lookup(1)

parts = raw.split(" of ", 1)
subject = parts[0].strip().lower()
target_str = parts[1].strip() if len(parts) == 2 else ""
has_of = bool(target_str)

if subject == "child" and has_of:
    try:
        if target_str.startswith("$"):
            parent = getattr(system, target_str[1:])
        elif target_str.startswith("#"):
            parent = lookup(int(target_str[1:]))
        else:
            parent = lookup(target_str)
    except (NoSuchObjectError, NoSuchPropertyError, AttributeError, ValueError):
        print(f"The aether cannot find a class called '{target_str}'.")
        return

    descendents = [o for o in parent.get_descendents() if o.pk != parent.pk]
    if not descendents:
        print(f"The aether offers nothing — {parent.title()} has no progeny.")
        return
    sample = random.sample(descendents, min(3, len(descendents)))
    lines = [f"Shapes coalesce from the lineage of {parent.title()} ({len(sample)}):"]
    for obj in sample:
        lines.append(f"  {obj.name} (#{obj.pk})")
    print("\n".join(lines))
    return

if subject == "location" and has_of:
    try:
        if target_str.startswith("$"):
            target = getattr(system, target_str[1:])
        elif target_str.startswith("#"):
            target = lookup(int(target_str[1:]))
        else:
            target = lookup(target_str)
    except (NoSuchObjectError, NoSuchPropertyError, AttributeError, ValueError):
        print(f"The aether cannot grasp '{target_str}'.")
        return

    room_class = system.room
    room = None
    cursor = target
    visited = 0
    while cursor is not None and visited < 32:
        if cursor.is_a(room_class):
            room = cursor
            break
        cursor = cursor.location
        visited += 1
    if room is None:
        print(f"The threads unravel — {target.title()} rests outside any room.")
        return
    print(f"The threads tighten around {target.title()}: it lies within {room.title()} (#{room.pk}).")
    return

if subject == "location":
    parent = system.room
    all_objects = [obj for obj in parent.get_descendents() if obj.pk != parent.pk]
    if not all_objects:
        print("The aether is silent. No locations can be found.")
        return
    count = random.randint(3, 7)
    sample = random.sample(all_objects, min(count, len(all_objects)))
    lines = [f"Impressions surface from the noise of the world ({len(sample)}):"]
    for obj in sample:
        lines.append(f"  {obj.name} (#{obj.pk})")
    print("\n".join(lines))
    return

print(f"The aether has no answer for '{subject}'.")
