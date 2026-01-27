#!moo verb @tunnel --on $programmer --dspec any

from moo.core import api, lookup, create

directions = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest", "up", "down"]
direction = api.parser.get_dobj_str()

if api.caller.location.has_property("exits"):
    exits = api.caller.location.get_property("exits")
else:
    exits = {}

if direction in exits:
    print("[color red]There is already an exit in that direction.[/red]")
    return  # pylint: disable=return-outside-function  # type: ignore

if api.parser.has_pobj("through"):
    door = api.parser.get_pobj("through")
    if not door.is_a(_.exit):
        print("[color red]The specified object is not an exit.[/color red]")
        return  # pylint: disable=return-outside-function  # type: ignore
else:
    door = create("{direction} exit", parents=[_.exit], location=None)
    door.set_property("source", api.caller.location)

dest = api.parser.get_pobj_str("to")
room = lookup(dest)
door.set_property("dest", room)

exits[direction] = door

api.caller.location.set_property("exits", exits)
print(f'[color yellow]Tunnelled an exit {direction} to "{room.name}".[/color yellow]')
