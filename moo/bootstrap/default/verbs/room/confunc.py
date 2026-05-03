#!moo verb confunc --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Called by the LambdaMOO server when a player connects in a room.

Tells everyone else in the room that the player has connected.  The
connecting player's own ``look_self()`` is handled by ``$player.confunc``
— calling it here too would render the room twice on connect.
"""

from moo.sdk import context

this.announce_all_but(context.player, f"{context.player} has connected.")
