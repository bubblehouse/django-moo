#!moo verb @edit edit_callback --on $note --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Edit a note's text.
"""

from moo.sdk import context, open_editor

if verb_name == "@edit":
    if not context.player.owns(this):
        print("You don't have permission to edit this note.")
        return
    content = this.get_property("text")
    callback = this.get_verb("edit_callback")
    open_editor(context.player, content, callback, content_type="text")
elif verb_name == "edit_callback":
    content = args[0]
    this.set_property("text", content)
