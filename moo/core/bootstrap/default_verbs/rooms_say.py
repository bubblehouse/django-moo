#!moo verb say --on $room

"""
This verb provides one of the basic ways in which players communicate. The action of the :say verb is very simple: it
`tells` the player what s/he has just said, and tells everyone else what the player said. The text spoken is passed to
all the objects in a room, not just the players, through the `tell` verbs on the objects in the room.

By overriding this verb, it is possible to provide all sorts of effects that work on everything said in the room. For
example, you could redirect messages to other rooms, or repeat messages to provide cavernous echoes.
"""
