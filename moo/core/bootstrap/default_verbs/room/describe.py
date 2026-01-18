#!moo verb describe --on $room --dspec this

from moo.core import lookup, api

obj = this  # pylint: disable=undefined-variable  # type: ignore

response = f"[bright_yellow]{obj.name}[/bright_yellow]\n"
if obj.has_property("description"):
    response += obj.get_property('description')
else:
    response += "[deep_sky_blue1]No description available.[/deep_sky_blue1]"

contents = obj.contents.filter(obvious=True)
if contents:
    response += "\n[yellow]Obvious contents:[/yellow]\n"
    for content in contents:
        response += f"{content.name}\n"

exits = obj.get_property("exits")
if exits:
    response += "\n[yellow]Exits:[/yellow]\n"
    for direction, _ in exits.items():
        response += f"{direction}\n"

return response  # pylint: disable=return-outside-function  # type: ignore
