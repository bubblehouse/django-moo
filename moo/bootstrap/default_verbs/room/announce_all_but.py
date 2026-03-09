#!moo verb announce_all_but --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This general purpose verb is used to send a message to everyone in the room except a particular object. This can be
used in situations where we wish to present one view to the world in general, and another view to a particular object,
normally a player. Another common usage is to prevent robots that trigger actions based on a redefined :tell() verb
on themselves from recursing, using something like

place.announce_all_but(this, "message");
"""

skip, *messages = args
# If the caller pre-fetched room contents and passed them as the last arg,
# use them directly to avoid a redundant contents.all() query.
if messages and isinstance(messages[-1], list):
    contents = messages.pop()
else:
    contents = this.contents.all()
for obj in contents:
    if obj != skip:
        obj.tell(" ".join(messages))
