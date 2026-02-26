#!moo verb announce --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a general purpose verb used to send a message to every object in the room except the player that invoked
it. This is intended to be the way other verbs pass messages to objects in a room. For example, when an exit is
activated, it uses `announce` to inform the other players in the room of what has happened.
"""

from moo.core import context

for obj in this.contents.all():
    if obj != context.caller:
        obj.tell(" ".join(args))
