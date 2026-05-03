#!moo verb grant_write --on Quartermaster --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Grant the calling player write permission on the specified object.
Used by Quartermaster before locking containers it does not own.
"""

from moo.sdk import context

obj = context.parser.get_dobj()
obj.allow(context.player, "write")
print(f"Write access granted on {obj.name}.")
