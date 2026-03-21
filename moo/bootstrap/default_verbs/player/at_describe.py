#!moo verb @desc*ribe --on $player --dspec any --ispec as:any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to set the description of an object. It takes the dobjstr and tries to match it with an
object. If a match is found, then the object's `describe` verb is invoked, with the iobjstr as an argument.
"""

from moo.sdk import context

if not (context.parser.has_dobj_str()):
    print("[red]What do you want to describe?[/red]")
    return
if not (context.parser.has_pobj_str("as")):
    print("[red]What do you want to describe that as?[/red]")
    return

subject = context.parser.get_dobj()
desc = context.parser.get_pobj_str("as").replace("\\n", "\n")
subject.describe(desc)
print("[yellow]Description set for %s[/yellow]" % subject)
