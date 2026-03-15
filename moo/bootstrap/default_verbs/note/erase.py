#!moo verb erase --on $note --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Erase all text stored on the note. Only the owner of a note can erase it.
"""

from moo.sdk import context

if context.player.owns(this):
    this.set_property("text", "")
