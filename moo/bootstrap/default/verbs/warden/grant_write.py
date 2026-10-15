#!moo verb grant_write --on Warden --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Grant the calling player write permission on the specified object and its properties.
Used by Warden before locking or unlocking exits it does not own.
"""

from moo.sdk import context

obj = context.parser.get_dobj()
obj.allow(context.player, "write")
# Each property row has its own owner and ACL, so object write alone does not cover them.
for prop in obj.properties.all():
    prop.allow(context.player, "write")
print(f"Write access granted on {obj.name}.")
