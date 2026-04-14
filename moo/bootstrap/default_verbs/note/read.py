#!moo verb r*ead --on $note --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Check if the note can be read by the person who is attempting to read it. If they have
permission to read it, the note text, which is stored in the property `text`, is shown to the player.
"""

from moo.sdk import context

if this.is_readable_by(context.player):
    text = this.get_property("text")
    print(f'"{text}"')
