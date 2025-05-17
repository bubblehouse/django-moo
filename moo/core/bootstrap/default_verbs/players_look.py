#!moo verb look inspect --on "player class" --dspec any --ispec at:any

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
else:
    obj = api.caller.location

print(system.describe(obj))
