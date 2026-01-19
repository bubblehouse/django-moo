#!moo verb moveto --on "Root Class"

"""
This verb is used to change the location of an object to be `where`. This verb is intended to be used by any other verbs
that must move an object to another location.

One important point to note is that this uses the set_task_perms() primitive to set the task permissions to those of
the thing that is being moved.

Again, by overriding the verb definition on an object, it is possible to augment or change the way an object is moved.
For example, you could keep a list of places visited by simply recording the where objects in a list every time this
function is called.
"""

from moo.core import set_task_perms

where = args[0]

set_task_perms(this)
this.location = where
this.save()
