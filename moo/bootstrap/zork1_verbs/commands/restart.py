#!moo verb restart --on $player
# pylint: disable=return-outside-function,undefined-variable
"""Restart the game (moves player to start, resets score and move count)."""

from moo.sdk import context

# Reset known per-player counters
context.player.set_property("zstate_score", 0)
context.player.set_property("zstate_moves", 0)

# Move player to the start room
start = _.zork_sdk.get_property("player_start")
context.player.location = start
context.player.save()
print("**** RESTART ****\n")
