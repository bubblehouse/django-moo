#!moo verb drop insert put --on $container --dspec this --ispec in:any --ispec on:any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb puts `object` into the container. The container is first checked to verify that it is open, if not an error message is printed.

For example, if you have a container named `pipe` and an object named `tobacco`, you could enter:

    put tobacco in pipe

If pipe is open, then tobacco will be put into the pipe. If you look at pipe you should see:

    pipe
    Contents:
        tobacco
"""

from moo.core import api

object = args[0] if args else api.parser.get_dobj()
subject = api.parser.get_pobj("in", "on") if api.parser.has_pobj("in", "on") else api.player.location

if not this.is_open():
    print("{this.title()} is closed.")
    return

this.move_to(subject)

chosen_prep = "in" if "in" in api.parser.prepositions else "on"
print(f"You placed {object.name} {chosen_prep} {subject.name}")
