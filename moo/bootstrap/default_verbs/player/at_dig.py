#!moo verb @dig @tunnel --on $programmer --dspec any --ispec "through:any"

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to create a room or exit, (that is, instances of the class `$room` or `$exit'. The verb
parses the arguments to determine the type and number of objects that are to be created. It uses the `create()` primitive,
with `$room` as a parent to create a room. Note that you can only use the `@dig` command to dig an exit from within a
room.
"""

from moo.core import api, create, lookup

directions = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest", "up", "down"]
direction = api.parser.get_dobj_str()

source = api.player.location
if source.match_exit(direction):
    print("[color red]There is already an exit in that direction.[/color red]")
    return

if api.parser.has_pobj("through"):
    door = api.parser.get_pobj("through")
    if not door.is_a(_.exit):
        print("[color red]The specified object is not an exit.[/color red]")
        return
    if not door.aliases.filter(alias=direction):
        door.aliases.create(alias=direction)
else:
    door = create(f"{direction} from {source.name}", parents=[_.exit], location=source)
    door.aliases.create(alias=direction)

if verb_name == "@dig":
    action = "Dug"
    dest = create(api.parser.get_pobj_str("to"), parents=[_.room], location=None)
else:
    action = "Tunnelled"
    dest = lookup(api.parser.get_pobj_str("to"))

door.set_property("source", source)
door.set_property("dest", dest)
source.add_exit(door)
dest.add_entrance(door)

print(f'[color yellow]{action} an exit {direction} to "{dest.name}".[/color yellow]')
