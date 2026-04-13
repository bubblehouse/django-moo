#!moo verb grant_move --on Tailor --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Grant the calling player move permission on the specified object.
Used by Tailor before take/drop operations on $things it does not own —
changing an object's location requires the `move` permission on that object.
"""

from moo.sdk import context

obj = context.parser.get_dobj()
obj.allow(context.player, "move")
print(f"Move access granted on {obj.name}.")
