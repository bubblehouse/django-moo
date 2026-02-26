#!moo verb @lock_for_open lock_for_open --on $container --dspec this --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb will lock the container with `object`. The container can only be opened if the player is holding `object`, or
the `object` is the player trying to open the container. The container will remained locked until it is unlocked.
"""

from moo.core import context

object = args[0] if args else context.parser.get_pobj("with")

this.set_property("open_key", object)
