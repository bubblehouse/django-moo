#!moo verb move --on $exit

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

"""
Move `thing` through the exit. It provides a general mechanism for moving any sort of object
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

from moo.core import context, PropertyDoesNotExist

thing = args[0]
source = this.get_property("source")
dest = this.get_property("dest")

if this.is_locked():
    thing.tell(this.nogo_msg(source, dest))
    source.announce_all_but(thing, this.onogo_msg(source, dest))
    return

# Fast path: skip bless_for_entry and accept for open rooms (saves 3-4 DB queries).
# bless_for_entry writes 2 properties; accept reads them back — all wasted I/O when
# the destination simply has free_entry=True and no lock.
try:
    free_entry = dest.get_property("free_entry")
except PropertyDoesNotExist:
    free_entry = False

if free_entry:
    accepted = True
else:
    dest.bless_for_entry(context.caller)
    accepted = dest.accept(thing)

# Pre-fetch room contents once per room to avoid a second contents.all() query
# inside each announce_all_but call.
source_contents = list(source.contents.all())
dest_contents = list(dest.contents.all())

if accepted:
    thing.tell(this.leave_msg(source, dest))
    source.announce_all_but(thing, this.oleave_msg(source, dest), source_contents)
    thing.moveto(dest)
    thing.tell(this.arrive_msg(source, dest))
    dest.announce_all_but(thing, this.oarrive_msg(source, dest), dest_contents)
else:
    thing.tell(this.nogo_msg(source, dest))
    source.announce_all_but(thing, this.onogo_msg(source, dest), source_contents)
