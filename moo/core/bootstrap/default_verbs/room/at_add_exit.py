#!moo verb @add-exit --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to add an exit to the current room. This is normally used when someone else has created
an exit they want to lead out of a room you own. The verb matches the direct object string with an object in the room
to get the object reference number for the exit. If the object found is not a descendant of the `$exit` object, the verb
is aborted with an error.

Otherwise, if the destination of the exit is readable and leads to a valid room, an attempt is made to add the exit
using the room's `add_exit` verb. If this fails, a suitable error message is sent to the user.
"""

from moo.core import api

door = api.parser.get_dobj()
if not door.is_a(_.exit):
    print("[color red]The specified object is not an exit.[/color red]")
    return

this.add_exit(door)
print(f'[color yellow]Added exit "{door.name}".[/color yellow]')
