#!moo verb @unlock_for_open unlock_for_open --on $container --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
This verb will remove the lock set by @lock_for_open. It can only be run by the owner of the container.
"""

this.set_property("open_key", None)
