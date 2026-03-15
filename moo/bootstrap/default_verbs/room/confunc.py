#!moo verb confunc --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Called by the LambdaMOO server when a player connects in a room.

The action coded into the $room class simply shows the player what the room looks like (using the `look_self` verb of
the room) and tells everyone else in the room that the player has connected.
"""

from moo.sdk import context

this.look_self()
this.announce(f"{context.player} has connected.")
