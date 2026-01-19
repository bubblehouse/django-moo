#!moo verb match --on "Root Class"

"""
This verb is used to find things that are located within this object.

It tries to match name to something in the contents list of this object, using object names and object aliases. This
verb uses the `obj.find()` method to do the actual searching. If a match is found, the object that matched is
returned. If more than one object matches, then AmbiguousObjectError is raised. If no match is found, then
NoSuchObjectError is raised.
"""

from moo.core import exceptions

qs = this.find(args[0])
if qs.count() == 0:
    raise this.objects.NoSuchObjectError(args[0])
elif qs.count() > 1:
    raise exceptions.AmbiguousObjectError(args[0], qs)
else:
    return qs.first()
