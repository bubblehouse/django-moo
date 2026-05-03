#!moo verb say --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Provide one of the basic ways in which players communicate. The action of the :say verb is very simple: it
`tells` the player what s/he has just said, and tells everyone else what the player said. The text spoken is passed to
all the objects in a room, not just the players, through the `tell` verbs on the objects in the room.

By overriding this verb, it is possible to provide all sorts of effects that work on everything said in the room. For
example, you could redirect messages to other rooms, or repeat messages to provide cavernous echoes.
"""

from moo.sdk import connected_players, context, send_gmcp

if context.parser.words:
    message = " ".join(context.parser.words[1:])
else:
    message = " ".join(args)

context.player.tell("You: " + message)
this.announce_all_but(context.player, context.player.name + ": " + message)

# GMCP Comm.Channel.Text to every connected player in the room (including the
# speaker, so accessibility clients can gag by `talker`). Intersecting
# connected_players against room contents avoids a per-object player lookup
# when the room has non-player items (furniture, keys, notes, etc.).
gmcp_event = {"channel": "say", "talker": context.player.name, "text": message}
connected = {p.pk for p in connected_players()}
for obj in this.contents.all():
    if obj.pk in connected:
        send_gmcp(obj, "Comm.Channel.Text", gmcp_event)
