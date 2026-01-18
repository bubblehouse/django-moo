#!moo verb look_self --on $room

"""
This verb overrides the $root_class definition of the verb `look_self` in order to provide a fuller description of a
room than the `description` property gives. This verb prints the room name, followed by the room's `description` property,
and then the list of contents of the room, using the room's `tell_contents` verb. This is what the player would see if
he was looking at the room.

The `description` property of the room is actually printed by using the passthrough() primitive to invoke the parent verb
`look_self`). Changes in the way an object's description is stored by the root class are invisible to this verb,
because of the way passthrough is used.
"""

return passthrough()  # pylint: disable=undefined-variable
