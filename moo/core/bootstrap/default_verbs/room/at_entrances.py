#!moo verb @entrances --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to list the entrances to the player's current location. Only the owner of a room may
list it's entrances. For every object kept in the room's entrances list, the exit name, object reference number and
aliases are displayed to the player.
"""
