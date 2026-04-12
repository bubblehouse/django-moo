#!moo verb grant_write --on Warden --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Grant the calling player write permission on the specified object.
Used by Warden before locking or unlocking exits it does not own.
"""

from moo.sdk import context

obj = context.parser.get_dobj()
obj.allow(context.player, "write")
print(f"Write access granted on {obj.name}.")
