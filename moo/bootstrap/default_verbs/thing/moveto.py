#!moo verb moveto --on $thing

# pylint: disable=return-outside-function,undefined-variable

"""
This verb should be used to move an `$thing` object from one location to another. It checks to see that `where` is a
valid object, and that the lock on `where` permits the object to enter. If this is the case, then the
`$root_class.moveto` verb is invoked to actually move the object, using `passthrough()`.
"""

where = args[0]

if where.is_unlocked_for(this):
    return passthrough(where)
