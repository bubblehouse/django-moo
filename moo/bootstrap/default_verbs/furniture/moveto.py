#!moo verb moveto --on $furniture

# pylint: disable=return-outside-function,undefined-variable

"""
Override of `$thing.moveto`. Furniture is fixed in place and cannot be moved by any means — taking,
dropping, giving, or teleporting. Returns `False` unconditionally, which causes `$thing.take` to
print the `take_failed_msg` property.
"""

return False
