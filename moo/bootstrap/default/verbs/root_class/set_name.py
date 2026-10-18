#!moo verb set_name --on $root_class --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Set the name of the object to value.

It returns `True` when the name is set, and `False` when a rule on the object
refuses the change. A caller without `write` gets :class:`PermissionError`, and
a name that is taken or not allowed raises :class:`UserError`, so the player
learns why. This verb and the `title` verb control access to the name of an
object. `@rename` goes through it, so a class can refuse a name by overriding it.
"""

from moo.sdk import require_caller_perms, UserError

require_caller_perms("write", this)

try:
    this.name = args[0]
    this.save()
except UserError:
    this.refresh_from_db()
    raise
except PermissionError:
    this.refresh_from_db()
    return False

return True
