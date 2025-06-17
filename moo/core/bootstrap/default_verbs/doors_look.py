#!moo verb look --on "door class" --dspec none --ispec through:any

from moo.core import api, lookup

system = lookup("system object")

door_description = api.parser.get_pobj_str("through")
exits = api.caller.location.get_property("exits", {})
for direction, exit in exits.items():  # pylint: disable=unused-variable,redefined-builtin
    if exit["door"].is_named(door_description):
        obj = exit["destination"]
        break
else:
    print(f"There is no door called {door_description} here.")
    return  # pylint: disable=return-outside-function  # type: ignore

print(system.describe(obj))
