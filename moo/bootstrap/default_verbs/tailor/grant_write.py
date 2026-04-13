#!moo verb grant_write --on Tailor --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Grant the calling player write permission on the specified object.
Used by Tailor before editing @gender, @messages, and other properties on
objects it does not own.
"""

from moo.sdk import context

obj = context.parser.get_dobj()
obj.allow(context.player, "write")
print(f"Write access granted on {obj.name}.")
