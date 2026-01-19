#!moo verb describe --on "Root Class"

"""
The `describe` verb is used to set the description property of an object.

This is only allowed if we have permission, determined using the $perm_utils:controls() verb.
By overriding this verb and the `description` verb, it is possible to completely change the
representation of an object description. This is done invisibly to anyone outside the object,
as long as you adhere to the same interface to `description` and `describe`.
"""

from moo.core import api

this.set_property("description", args[0])
