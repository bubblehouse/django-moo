#!moo verb @listgag listgag --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
List the objects in the player's gag lists. If the gag lists are not empty, a
list of the names of the players in the `gaglist` property on the player, and the objects in the `object_gaglist`
property are produced.

The verb uses a test based on the `context.parser` object, to determine if it is being called by another verb, or
invoked by a player as a command. If `context.parser` returns `None` (and hence is not `True`), then the verb is being
invoked as a player command. When False, the verb is being invoked by another verb, and therefore returns JSON.

TODO: In addition, the verb checks through the gag lists of all the player's in the database, to see if the player who
TODO: invoked the command is listed in anyone else's gag list. If this is the case, a list of the people doing the
TODO: gagging is printed.
"""

from moo.sdk import context, NoSuchPropertyError

player = context.player

try:
    gaglist = player.gaglist
except NoSuchPropertyError:
    gaglist = []

try:
    object_gaglist = player.object_gaglist
except NoSuchPropertyError:
    object_gaglist = []

if not context.parser:
    # Called directly (verb-to-verb or test) — print and return structured data
    print("Gagged players:")
    for p in gaglist:
        print(f"  {p.name}")
    if not gaglist:
        print("  None")
    print("Gagged objects:")
    for o in object_gaglist:
        print(f"  {o.name}")
    if not object_gaglist:
        print("  None")
else:
    # Called as a player shell command — use tell() for output visible in the response window
    player.tell("Gagged players:")
    for p in gaglist:
        player.tell(f"  {p.name}")
    if not gaglist:
        player.tell("  None")
    player.tell("Gagged objects:")
    for o in object_gaglist:
        player.tell(f"  {o.name}")
    if not object_gaglist:
        player.tell("  None")
