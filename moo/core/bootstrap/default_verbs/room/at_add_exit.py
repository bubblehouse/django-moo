#!moo verb @add-exit --on $room --dspec any

"""
This is a player command used to add an exit to the current room. This is normally used when someone else has created
an exit they want to lead out of a room you own. The verb matches the direct object string with an object in the room
to get the object reference number for the exit. If the object found is not a descendant of the `$exit` object, the verb
is aborted with an error.

Otherwise, if the destination of the exit is readable and leads to a valid room, an attempt is made to add the exit
using the room's `add_exit` verb. If this fails, a suitable error message is sent to the user.
"""
