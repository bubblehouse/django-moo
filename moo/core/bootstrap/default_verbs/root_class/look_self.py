#!moo verb look_self --on "Root Class"

"""
The `look_self` verb on any object is used to tell another object what this object looks like, in detail.

This verb makes use of the `description` verb on the object to obtain a string or list of strings to print.
It would be possible to override this verb to produce a special description for an object. However, any
other verbs that use the `description` verb of the object will not see the extra information added by the
overriding function. The `$room` class overrides this verb with code to print the room name and a list of
objects that are in the room.
"""

from moo.core import api

return this.description()  # pylint: disable=return-outside-function  # type: ignore
