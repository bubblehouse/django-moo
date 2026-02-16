#!moo verb set_name --on $root_class --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb sets the name of the object to value. It returns `True` if the name was set to the value successfully,
otherwise it returns `False`. This verb and the `title` verb are used to control access to the name property of an
object.
"""

try:
    this.name = args[0]
    this.save()
except:  # pylint: disable=bare-except
    return False

return True
