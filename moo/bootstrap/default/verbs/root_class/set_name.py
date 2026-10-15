#!moo verb set_name --on $root_class --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Set the name of the object to value. It returns `True` if the name was set to the value successfully,
otherwise it returns `False`. This verb and the `title` verb are used to control access to the name property of an
object.
"""

from moo.sdk import require_caller_perms

require_caller_perms("write", this)

try:
    this.name = args[0]
    this.save()
except:  # pylint: disable=bare-except
    return False

return True
