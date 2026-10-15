#!moo verb moveto --on $root_class

# pylint: disable=return-outside-function,undefined-variable

"""
Change the location of an object to be `where`. This verb is intended to be used by any other verbs
that must move an object to another location.

The calling code's owner (see `caller_perms()`) needs `move` permission on the object, unless the object is the player
who started the task: a player can always move themselves. The move itself then runs with the permissions of the
object's owner, so the destination's `accept` decides whether it is let in.

Again, by overriding the verb definition on an object, it is possible to augment or change the way an object is moved.
For example, you could keep a list of places visited by simply recording the where objects in a list every time this
function is called.
"""

from moo.sdk import context, require_caller_perms, set_task_perms

where = args[0]

# A player may move themselves through anyone's code; moving anything else
# needs "move" permission for the calling verb's owner.
if context.player is None or this.pk != context.player.pk:
    require_caller_perms("move", this)

with set_task_perms(this.owner):
    this.location = where
    this.save()
return True
