#!moo verb describe --on "room class" --method

from moo.core import lookup

obj = args[1]  # pylint: disable=undefined-variable  # type: ignore
system = lookup("system object")

response = f"[bright_yellow]{obj.name}[/bright_yellow]\n"
response += system.describe(obj)

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
