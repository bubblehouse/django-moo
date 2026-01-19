#!moo verb accept --on "Root Class"

"""
This verb is used to control what objects are permitted to be placed inside other objects. If this verb returns
`False`, then the object where cannot be moved into this object. Conversely, if the verb returns a non-zero value, the
object is allowed to be placed inside this object. The verb is called by the server when it changes the `location`
property of an object.

The `$root_class` definition returns `False`. In this case, no objects are allowed inside any objects that are
children of the `$root_class`.
"""

thing = args[0]

return False
