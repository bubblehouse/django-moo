#!moo verb @dig --on $programmer --dspec any --ispec "through:any"

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to create a room or exit, (that is, instances of the class `$room` or `$exit'. The verb
parses the arguments to determine the type and number of objects that are to be created. It uses the `create()` primitive,
with `$room` as a parent to create a room. Note that you can only use the `@dig` command to dig an exit from within a
room.
"""

from moo.core import api, create

directions = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest", "up", "down"]
direction = api.parser.get_dobj_str()

if api.caller.location.has_property("exits"):
    exits = api.caller.location.get_property("exits")
else:
    exits = {}

if direction in exits:
    print("[color red]There is already an exit in that direction.[/color red]")
    return

if api.parser.has_pobj("through"):
    door = api.parser.get_pobj("through")
    if not door.is_a(_.exit):
        print("[color red]The specified object is not an exit.[/color red]")
        return
else:
    door = create("{direction} exit", parents=[_.exit], location=None)

dest = api.parser.get_pobj_str("to")
room = create(dest, parents=[_.room], location=None)
door.set_property("source", api.caller.location)
door.set_property("dest", room)

exits[direction] = door

api.caller.location.set_property("exits", exits)
print(f'[color yellow]Dug an exit {direction} to "{room.name}".[/color yellow]')
