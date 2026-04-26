#!moo verb @create make --on $builder --dspec any --ispec from:any --ispec in:any

# pylint: disable=return-outside-function,undefined-variable

"""
Create an instance of an object or class. The new object is placed in the
player's inventory by default — players typically don't own the room they are
standing in, so dropping new objects there would surprise the room owner (and
may be rejected by the room's `accept` verb). Pass an explicit location with
``in <location>`` to place the object somewhere else, or ``in the void`` to
leave it unlocated.

Usage:
    @create <name>
    @create <name> from <parent>
    @create <name> in <location>
    @create <name> from <parent> in <location>
    @create <name> in the void
"""

from moo.sdk import context, create, set_task_perms

if not (context.parser.has_dobj_str()):
    print("[yellow]What do you want to create?[/yellow]")
    return

name = context.parser.get_dobj_str()

# Resolve location before calling create() so it can be placed via ORM,
# bypassing any moveto verb (e.g. $furniture.moveto returns False for non-wizards).
location = None
place_in_void = False
explicit_location = False
if context.parser.has_pobj_str("in"):
    location_str = context.parser.get_pobj_str("in").lower()
    if location_str == "void":
        place_in_void = True
    else:
        location = context.parser.get_pobj("in", lookup=True)
        explicit_location = True

if not place_in_void and location is None:
    location = context.player

with set_task_perms(context.player):
    new_obj = create(name, owner=context.player, location=location)

if place_in_void:
    placement = "in the void"
elif explicit_location:
    placement = f"in {location}"
else:
    room = context.player.location
    if room is not None and room.owner_id != context.player.pk:
        placement = f"in your inventory (you don't own {room})"
    else:
        placement = "in your inventory"

print(f"[yellow]Created {new_obj} {placement}.[/yellow]")

if context.parser.has_pobj_str("from"):
    with set_task_perms(context.player):
        parent = context.parser.get_pobj("from", lookup=True)
        new_obj.add_parent(parent)
    print(f"[yellow]Transmuted {new_obj} to {parent}.[/yellow]")
