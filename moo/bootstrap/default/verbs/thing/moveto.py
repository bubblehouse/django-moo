#!moo verb moveto --on $thing

# pylint: disable=return-outside-function,undefined-variable

"""
Move an `$thing` object from one location to another. It checks to see that `where` is a
valid object, and that the lock on `where` permits the object to enter. If this is the case, then the
`$root_class.moveto` verb is invoked to actually move the object, using `passthrough()`.
"""

from moo.sdk import context, require_caller_perms

where = args[0]

# A player may move themselves through anyone's code; moving anything else
# needs "move" permission for the calling verb's owner.
if context.player is None or this.pk != context.player.pk:
    require_caller_perms("move", this)

# Clear placement for any objects placed on this one in the current room.
# Runs before the move so this.location is still the source room.
if this.location:
    for placed in list(this.placed_objects.filter(location=this.location).all()):
        placed.clear_placement()

if where.is_unlocked_for(this):
    return passthrough(where)
return False
