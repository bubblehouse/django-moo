#!moo verb make --on "Generic Programmer" --dspec any --ispec from:any

from moo.core import api, create, lookup

if not (api.parser.has_dobj_str()):
    print("[color yellow]What do you want to make?[/color yellow]")
    return  # pylint: disable=return-outside-function  # type: ignore

name = api.parser.get_dobj_str()
new_obj = create(name)
print("[color yellow]Created %s[/color yellow]" % new_obj)

if api.parser.has_pobj_str("from"):
    parent_name = api.parser.get_pobj_str("from")
    try:
        parent = lookup(parent_name)
        new_obj.parents.add(parent)
    except new_obj.DoesNotExist:
        print(f"[color red]No such object: {parent_name}[/color red]")
        return  # pylint: disable=return-outside-function  # type: ignore
    print("[color yellow]Transmuted %s to %s[/color yellow]" % (new_obj, parent))
