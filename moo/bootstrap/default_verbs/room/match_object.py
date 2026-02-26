#!moo verb match_object --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This is the verb used to search the player's locale for an object that has the name or pseudonym name. The verb
searches the room contents and the players contents (or possessions) for a match. If a match is found, then the object
is returned. If name matches more than one object, then AmbiguousObjectError is raised. If no match is found, then
Object.DoesNotExist is raised.

The verb `match_object` is the one to use to map names of objects to object references, when referring to objects that the
player is able to see in his current location. This includes objects that the player might be carrying, but does not
include objects that are contained in other objects.
"""

from moo.core import context, AmbiguousObjectError

name = args[0]

qs = this.find(name)
if not qs:
    qs = context.player.find(name)
if not qs:
    raise this.DoesNotExist(name)
elif len(qs) > 1:
    raise AmbiguousObjectError(name, matches=qs.all())

return qs[0]
