#!moo verb describe --on "System Object" --dspec this

from moo.core import api

obj = args[1]  # pylint: disable=undefined-variable  # type: ignore

if obj.has_verb("describe"):
    v = obj.get_verb("describe")
    return v()  # pylint: disable=return-outside-function  # type: ignore
elif obj.has_property("description"):
    description = obj.get_property("description")
    return f"[bright_yellow]{obj.name}[/bright_yellow]\n[deep_sky_blue1]{description}[/deep_sky_blue1]"  # pylint: disable=return-outside-function  # type: ignore
else:
    return "[deep_pink4 bold]Not much to see here.[/deep_pink4 bold]"  # pylint: disable=return-outside-function  # type: ignore
