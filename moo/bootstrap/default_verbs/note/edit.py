#!moo verb @edit edit_callback --on $note --dspec this --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Edit a note's text.

Syntax:
    @edit <note>              open full-screen editor
    @edit <note> with "<text>"  set text inline without opening the editor
"""

from moo.sdk import context, open_editor

if verb_name == "@edit":
    if not context.player.owns(this):
        print("You don't have permission to edit this note.")
        return
    if context.parser.has_pobj_str("with"):
        new_text = context.parser.get_pobj_str("with")
        new_text = new_text.replace("\\n", "\n")
        this.set_property("text", new_text)
        print(f"Text set on {this}")
    else:
        content = this.get_property("text")
        callback = this.get_verb("edit_callback")
        open_editor(context.player, content, callback, content_type="text", title=str(this))
elif verb_name == "edit_callback":
    content = args[0]
    this.set_property("text", content)
