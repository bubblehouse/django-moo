#!moo verb say --on $room --dspec any

"""
This verb provides one of the basic ways in which players communicate. The action of the :say verb is very simple: it
`tells` the player what s/he has just said, and tells everyone else what the player said. The text spoken is passed to
all the objects in a room, not just the players, through the `tell` verbs on the objects in the room.

By overriding this verb, it is possible to provide all sorts of effects that work on everything said in the room. For
example, you could redirect messages to other rooms, or repeat messages to provide cavernous echoes.
"""

from moo.core import api, lookup

if api.parser.words:
    message = " ".join(api.parser.words[1:])
else:
    message = " ".join(args)

api.caller.tell("You: " + message)
for obj in this.contents.all():
    if obj != api.caller:
        obj = lookup(obj.id)
        obj.tell(api.caller.name + ": " + message)
