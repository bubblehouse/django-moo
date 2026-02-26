#!moo verb description --on $root_class

# pylint: disable=return-outside-function,undefined-variable

"""
The `description` verb on any object is supposed to return a string or list of strings describing the object in the detail
someone would notice if they were specifically looking at it.

The default implementation of the `look` command (defined on the $room class), prints this description using the `look_self`
verb on the object. `look_self` uses `description` to obtain the text to display.
"""

from moo.core import context

description = ""
if this.has_property("description"):
    description = this.get_property("description")

if description:
    return f"[color deep_sky_blue1]{description}[/color deep_sky_blue1]"
else:
    return "[color deep_pink4 bold]Not much to see here.[/color deep_pink4 bold]"
