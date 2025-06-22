#!moo verb go --on "player class" --dspec any

from moo.core import api

direction = api.parser.get_dobj_str()

if api.caller.location.has_property("exits"):
    exits = api.caller.location.get_property("exits")
else:
    exits = {}

if direction not in exits:
    print("[red]There is no exit in that direction.[/red]")
    return  # pylint: disable=return-outside-function  # type: ignore

exit_info = exits[direction]
destination = exit_info["destination"]
door = exit_info.get("door")

if door and door.is_locked():
    print(f"[red]The {door.name} is locked.[/red]")
    return  # pylint: disable=return-outside-function  # type: ignore

api.caller.location = destination
api.caller.save()
print(f"You go {direction}.")
