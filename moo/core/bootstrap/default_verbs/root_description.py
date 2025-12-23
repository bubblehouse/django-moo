#!moo verb description --on "Root Class"

"""
The `description` verb on any object is supposed to return a string or list of strings describing the object in the detail
someone would notice if they were specifically looking at it.

The default implementation of the `look` command (defined on the $room class), prints this description using the `look_self`
verb on the object. `look_self` uses `description` to obtain the text to display.
"""

from moo.core import api

if this.has_property("description"):
    description = this.get_property("description")
    return f"[bright_yellow]{this.name}[/bright_yellow]\n[deep_sky_blue1]{description}[/deep_sky_blue1]"  # pylint: disable=return-outside-function  # type: ignore
else:
    return "[deep_pink4 bold]Not much to see here.[/deep_pink4 bold]"  # pylint: disable=return-outside-function  # type: ignore
