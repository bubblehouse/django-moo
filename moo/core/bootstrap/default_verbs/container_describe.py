#!moo verb describe --on "container class" --method

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

return response  # pylint: disable=return-outside-function  # type: ignore
