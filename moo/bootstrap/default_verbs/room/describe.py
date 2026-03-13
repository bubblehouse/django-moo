#!moo verb describe --on $room --dspec this

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

from moo.core import lookup, context, NoSuchPropertyError

obj = this

response = ""

try:
    response += obj.get_property('description')
except NoSuchPropertyError:
    response += "[deep_sky_blue1]No description available.[/deep_sky_blue1]"

contents = obj.contents.filter(obvious=True)
if contents:
    response += "\n[yellow]Obvious contents:[/yellow]\n"
    for content in contents:
        response += f"{content.name}\n"

return response
