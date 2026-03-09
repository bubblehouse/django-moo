#!moo verb describe --on $room --dspec this

# pylint: disable=return-outside-function,undefined-variable

from moo.core import lookup, context, PropertyDoesNotExist

obj = this

response = ""

try:
    response += obj.get_property('description')
except PropertyDoesNotExist:
    response += "[color deep_sky_blue1]No description available.[/color deep_sky_blue1]"

contents = obj.contents.filter(obvious=True)
if contents:
    response += "\n[color yellow]Obvious contents:[color /yellow]\n"
    for content in contents:
        response += f"{content.name}\n"

return response
