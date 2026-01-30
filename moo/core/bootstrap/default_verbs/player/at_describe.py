#!moo verb @desc*ribe --on $player --dspec any --ispec as:any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to set the description of an object. It takes the dobjstr and tries to match it with an
object. If a match is found, then the object's `describe` verb is invoked, with the iobjstr as an argument.
"""

from moo.core import api

if not (api.parser.has_dobj_str()):
    print("[red]What do you want to describe?[/red]")
    return
if not (api.parser.has_pobj_str("as")):
    print("[red]What do you want to describe that as?[/red]")
    return

subject = api.parser.get_dobj()
subject.describe(api.parser.get_pobj_str("as"))
print("[color yellow]Description set for %s[/color yellow]" % subject)
