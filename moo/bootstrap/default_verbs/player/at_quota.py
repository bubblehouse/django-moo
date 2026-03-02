#!moo verb @quota at_quota --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to print a player's current building quota. This is a numerical value of the number
of objects that the player may create without recycling anything. Quotas are used to limit the number of objects that
can be created, in principle to allow the game administrators to quality control the things that are placed in the
database.

With no argument, the player's quota is displayed, taken from the property `ownership_quota`. If an argument is given
in `parser.get_dobj_str()`, it is taken as a player name, and matched to find a player object reference. If one is
found, and the user is a wizard, then the value of that player's `ownership_quota` is returned. Otherwise, a
`permission denied' message is returned.
"""

from moo.core import context, lookup

if args:
    player_name = args[0]
elif context.parser.has_dobj_str():
    player_name = context.parser.get_dobj_str()
else:
    player_name = None

if player_name:
    if context.player.is_wizard():
        player_obj = lookup(player_name)
        if player_obj and player_obj.is_player():
            print(f"{player_obj.name}'s quota is {player_obj.ownership_quota}.")
        else:
            print(f"No player named '{player_name}' found.")
else:
    print(f"Your quota is {context.player.ownership_quota}.")
