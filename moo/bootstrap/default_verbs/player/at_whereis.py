#!moo verb @whereis whereis --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Locate a player in the virtual world. The code, shown below, allows any player to
locate any other player. If no argument is given, a list of the locations of all the currently connected players is
printed.

If an argument is given, the verb attempts to match with one or more player names. If no valid matches are found, a
suitable error message is printed by invoking the verb $command_utils:player_match_result. That verb returns a list.
The first element indicates whether any of the elements of the argument list didn't match. The rest of the list
contains the objects references that did match.

The verb runs through the list of object references, and reports the string returned by each player's whereis_location_msg verb.
"""

from moo.core import context, lookup

targets = args if args else [context.parser.get_dobj_str()]
matched = []
unmatched = []
for target in targets:
    try:
        result = lookup(target)
        matched.append(result)
    except type(this).NotFoundError:
        unmatched.append(target)

print("Found the following players:")
for player in matched:
    print(player.whereis_location_msg())
