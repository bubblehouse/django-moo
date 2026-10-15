#!moo verb @unlock_for_open unlock_for_open --on $container --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Remove the lock set by @lock_for_open. It can only be run by the owner of the container.
"""

from moo.sdk import context

context.player.is_allowed("write", this, fatal=True)
this.set_property("open_key", None)
print(f"Lock removed from {this.name}.")
