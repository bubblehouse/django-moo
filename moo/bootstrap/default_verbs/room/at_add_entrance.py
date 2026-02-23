#!moo verb @add-entrance --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to add an entrance to the current room. This follows much the same sequence as for the
`@add-exit`. An attempt is made to match the direct object supplied with an object in the room. If this fails, the verb
is aborted with a suitable error message.

Otherwise, if the object found is a descendant of the `$exit` class, then the exit is checked to make sure it goes to
this room. If this is the case, then the exit is added as an entrance using the room's `add_entrance` verb.
"""

from moo.core import api

door = api.parser.get_dobj()
if not door.is_a(_.exit):
    print("[color red]The specified object is not an exit.[/color red]")
    return

this.add_entrance(door)
print(f'[color yellow]Added entrance "{door.name}".[/color yellow]')
