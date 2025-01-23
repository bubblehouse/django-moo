#!moo verb look inspect --on "player class" --ability

from moo.core import api

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

print(f"[bright_yellow]{obj.name}[/bright_yellow]")
if obj.has_property("description"):
    print(f"[deep_sky_blue1]{obj.get_property('description')}[/deep_sky_blue1]")
else:
    print("[deep_pink4 bold]Not much to see here.[/deep_pink4 bold]")

contents = obj.contents.filter(obvious=True)
if contents:
    print("[yellow]Obvious contents:[/yellow]")
    for content in contents:
        print(f"{content.name}")

# if you're looking at the room you're in, show the exits
if obj == api.caller.location and obj.has_property("exits"):
    exits = api.caller.location.get_property("exits")
    if exits:
        print("[yellow]Exits:[/yellow]")
        for direction, _ in exits.items():
            print(direction)
