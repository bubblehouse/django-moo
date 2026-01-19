#!moo verb @add-entrance --on $room --dspec any

"""
This is a player command used to add an entrance to the current room. This follows much the same sequence as for the
`@add-exit`. An attempt is made to match the direct object supplied with an object in the room. If this fails, the verb
is aborted with a suitable error message.

Otherwise, if the object found is a descendant of the `$exit` class, then the exit is checked to make sure it goes to
this room. If this is the case, then the exit is added as an entrance using the room's `add_entrance` verb.
"""
