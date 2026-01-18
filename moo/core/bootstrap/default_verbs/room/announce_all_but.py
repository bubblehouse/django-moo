#!moo verb announce_all_but --on $room

"""
This general purpose verb is used to send a message to everyone in the room except a particular object. This can be
used in situations where we wish to present one view to the world in general, and another view to a particular object,
normally a player. Another common usage is to prevent robots that trigger actions based on a redefined :tell() verb
on themselves from recursing, using something like

place.announce_all_but(this, "message");
"""

skip, *messages = args
for obj in this.contents:
    if obj != skip:
        obj.tell(" ".join(messages))
