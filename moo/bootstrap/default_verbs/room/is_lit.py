#!moo verb is_lit --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Returns True if the room has enough light to see.

A dark room (``dark=True``) is considered lit only if ``get_lights()`` returns
at least one object currently providing light.
"""

if not this.get_property("dark"):
    return True
return bool(this.get_lights())
