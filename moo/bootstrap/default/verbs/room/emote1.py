#!moo verb emote1 --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Called by the emote verb to send the emote text to the other objects in the room. By overriding this
verb, it is possible to create special effects for emote actions that are only seen by the other people in a room.
`args[0]` is the full line, the actor's name first. :emote1 uses $room:announce to send it.
"""

from moo.sdk import context

this.announce(args[0])
