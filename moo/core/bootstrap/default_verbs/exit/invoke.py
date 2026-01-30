#!moo verb invoke --on $exit

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to trigger an exit. In the `$room` class, when a player elects to move through an exit, this verb is
called to move the player through the exit. The code for this verb is very simple. It calls the exit's `move` verb, with
the player object as an argument.

This is the verb to use for moving players through exits. It does not allow objects to be moved. For that, a direct
call to the exit's `move` verb is needed, with the object you wish to move through the exit as an argument.
"""

from moo.core import UserError

player = args[0]
if not player.is_player():
    raise UserError("Only players can use exits.")
this.move(player)
