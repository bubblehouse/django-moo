#!moo verb look inspect --on "player class" --dspec none --ispec at:any --ispec through:any

from moo.core import api, lookup

system = lookup("system object")

if api.parser.has_dobj():
    obj = api.parser.get_dobj()
elif api.parser.has_dobj_str():
    dobj_str = api.parser.get_dobj_str()
    qs = api.caller.find(dobj_str) or api.caller.location.find(dobj_str)
    if not qs:
        print(f"There is no '{dobj_str}' here.")
        return  # pylint: disable=return-outside-function  # type: ignore
    obj = qs[0]
elif api.parser.has_pobj_str("at"):
    pobj_str = api.parser.get_pobj_str("at")
    qs = api.caller.find(pobj_str) or api.caller.location.find(pobj_str)
    if not qs:
        print(f"There is no '{pobj_str}' here.")
        return  # pylint: disable=return-outside-function  # type: ignore
    obj = qs[0]
elif api.parser.has_pobj_str("through"):
    door_description = api.parser.get_pobj_str("through")
    exits = api.caller.location.get_property("exits", {})
    for direction, exit in exits.items():  # pylint: disable=unused-variable,redefined-builtin
        if exit["door"].is_named(door_description):
            obj = exit["destination"]
            break
    else:
        print(f"There is no door called {door_description} here.")
        return  # pylint: disable=return-outside-function  # type: ignore
else:
    obj = api.caller.location

print(system.describe(obj))
