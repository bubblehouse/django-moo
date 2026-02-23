#!moo verb announce_all --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is another general purpose verb used to send a message to every object in the room. It is used for messages
that we wish everyone to see, with no exceptions.
"""

messages = args
for obj in this.contents.all():
    obj.tell(" ".join(messages))
