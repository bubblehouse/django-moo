#!moo verb @rooms --on $player --dspec none

# pylint: disable=return-outside-function,undefined-variable

"""
List every room instance in the world as a flat list with object IDs.
Useful for agents that need to discover what rooms exist.

Usage:
    @rooms   — show all room instances with #N and name
"""

from moo.sdk import context, lookup, open_paginator

system = lookup(1)
room_class = system.room

rooms = [obj for obj in room_class.get_descendents() if obj.pk != room_class.pk]

if not rooms:
    print("[red]No rooms found.[/red]")
    return

lines = ["Rooms in the world:"]
for room in rooms:
    lines.append(f"  #{room.pk}  {room.name}")

open_paginator(context.player, "\n".join(lines), content_type="text")
