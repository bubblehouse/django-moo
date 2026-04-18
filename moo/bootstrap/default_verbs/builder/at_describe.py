#!moo verb @desc*ribe describe_callback --on $builder --dspec any --ispec as:any

# pylint: disable=return-outside-function,undefined-variable

"""
Set the description of an object.

Syntax:
    @describe <object> as "<text>"   — set description directly
    @describe <object>               — open editor to write the description

The editor is pre-populated with the current description (if any).
When the editor is saved, the description is updated on the object.
"""

from moo.sdk import context, open_editor, lookup, NoSuchPropertyError

if verb_name == "@describe":
    if not context.parser.has_dobj_str():
        print("[red]What do you want to describe?[/red]")
        return

    subject = context.parser.get_dobj()

    if context.parser.has_pobj_str("as"):
        desc = context.parser.get_pobj_str("as").replace("\\n", "\n")
        subject.describe(desc)
        print("[yellow]Description set for %s[/yellow]" % subject)
    else:
        try:
            current_desc = subject.get_property("description")
        except NoSuchPropertyError:
            current_desc = ""
        callback = context.player.get_verb("describe_callback")
        open_editor(context.player, current_desc or "", callback, subject.pk, content_type="text", title=str(subject))

elif verb_name == "describe_callback":
    desc = args[0]
    subject = lookup(args[1])
    subject.describe(desc)
    print("[yellow]Description set for %s[/yellow]" % subject)
