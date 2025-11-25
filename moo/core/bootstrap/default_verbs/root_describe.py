#!moo verb describe --on "Root Class"

"""
The `describe` verb is used to set the description property of an object.

This is only allowed if we have permission, determined using the $perm_utils:controls() verb.
By overriding this verb and the `description` verb, it is possible to completely change the
representation of an object description. This is done invisibly to anyone outside the object,
as long as you adhere to the same interface to `description` and `describe`.
"""

from moo.core import api

if not (api.parser.has_dobj_str()):
    print("[red]What do you want to describe?[/red]")
    return  # pylint: disable=return-outside-function  # type: ignore
if not (api.parser.has_pobj_str("as")):
    print("[red]What do you want to describe that as?[/red]")
    return  # pylint: disable=return-outside-function  # type: ignore

subject = api.parser.get_dobj()
subject.set_property("description", api.parser.get_pobj_str("as"))
print("[color yellow]Description set for %s[/color yellow]" % subject)
