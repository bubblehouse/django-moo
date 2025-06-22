#!moo verb describe --on "author class" --dspec any --ispec as:any

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
