#!moo verb move --on $exit

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to move `thing` through the exit. It provides a general mechanism for moving any sort of object
through the exit, not necessarily just players. The code for this verb performs a number of actions. First, the lock on
the exit is checked to see if thing is allowed to use the exit. If this is not the case, the `nogo_msg` and `onogo_msg`
text is sent to thing and everyone else in thing's location, respectively.

If the object is allowed to use the exit, it is blessed for entry to the destination room. This is done to ensure that
the object will be accepted by the destination room. It provides a way to stop objects moving into a room by any means
other than an exit leading into the room. By simply prohibiting all objects from entering the room, the only way in is
then to use an exit that leads into that room.

If the object is accepted by the room, determined using the $room:accept verb, then the leave messages are printed to
thing and the other people in the room. Then thing:moveto is invoked to move the object from the current room to the
destination of the exit. Once this has been done, the arrive messages for the exit are printed out to thing and the
destination room's occupants.
"""

from moo.core import api

thing = args[0]
source = this.get_property("source")
dest = this.get_property("dest")

#TODO: check lock on exit to see if thing can use it

dest.bless_for_entry(api.caller)
if this.dest.accept(thing):
    thing.tell(this.leave_msg())
    source.announce_all_but(thing, this.oleave_msg())
    thing.moveto(this.dest)
    thing.tell(this.arrive_msg())
    dest.announce_all_but(thing, this.oarrive_msg())
else:
    thing.tell(this.nogo_msg())
    source.announce_all_but(thing, this.onogo_msg())
