#!moo verb @checkexits checkexits --on $builder --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Connectivity guard (spec 200, item M): report whether the current room (or a
named one) is a potential trap — no way out, or a one-way exit whose
destination has no exit back.  Run at build completion to catch black holes
before players fall into them.
"""

from moo.sdk import context, check_room_connectivity

if context.parser.has_dobj_str():
    room = context.parser.get_dobj(lookup=True)
else:
    room = context.player.location

if room is None:
    print("You're not anywhere to check.")
    return

report = check_room_connectivity(room)
if not report["issues"]:
    print(f"[green]{room.name} is well-connected.[/green]")
    return

print(f"[yellow]Connectivity issues for {room.name}:[/yellow]")
for issue in report["issues"]:
    print(f"  - {issue}")
