#!moo verb accept --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to determine if a player will allow `thing` to be moved into his/her inventory. The verb defined for
the `$player` class allows anything that is not a player to be moved into the player's possession. You could override
this verb to restrict the sorts of things you would want other people to be able to place on your person.
"""

thing = args[0]
return not thing.is_player()
