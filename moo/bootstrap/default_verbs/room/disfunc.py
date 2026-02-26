#!moo verb disfunc --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is called by the LambdaMOO server when a player disconnects from the game.

The $room class definition of this verb moves the player home if s/he is not already there, using the :moveto verb on
the player. One possible enhancement of this verb, already implemented in some MOOs, is to include a time delay
between disconnection and movement of the player to his/her home. This would allow some tolerance of disconnection
due to network problems.
"""

from moo.core import context

home = context.player.home or _.player_start
if context.player.location != home:
    context.player.moveto(context.player.home)
this.announce(f"{context.player} has disconnected.")
