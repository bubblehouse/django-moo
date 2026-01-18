#!moo verb emote1 --on $room

"""
This verb is invoked by the emote verb to send the emote text to the other objectss in the room. By overriding this
verb, it is possible to create special effects for emote actions that are only seen by the other people in a room.
:emote1 uses $room:announce to send it's message.
"""

this.announce(args)
