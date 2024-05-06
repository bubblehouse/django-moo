from moo.core import api

if(api.parser.has_dobj()):
    obj = api.parser.get_dobj()
elif(api.parser.has_dobj_str()):
    dobj_str = api.parser.get_dobj_str()
    qs = api.caller.find(dobj_str)
    if not qs:
        print(f"There is no '{dobj_str}' here.")
        return  # pylint: disable=return-outside-function  # type: ignore
    obj = qs[0]
else:
    obj = api.caller.location

qs = obj.properties.filter(name="description")
if qs:
    print(f"""
[yellow]{obj.name}[/yellow]

[deep_sky_blue1]{qs[0].value}[/deep_sky_blue1]
""")
else:
    print(f"""
[yellow]{obj.name}[/yellow]

[deep_pink4 bold]Not much to see here.[/deep_pink4 bold]
""")
