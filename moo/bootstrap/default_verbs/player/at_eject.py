#!moo verb @eject --on $player --dspec any --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to remove objects from rooms or the player's inventory. The indirect object is used
to specify what the direct object is to be ejected from.

If neither of the special cases match, the direct and indirect object are matched on, to give an object reference to
use. Suitable error messages are printed if a match is not found. If matches are found, then a sequence of message
printing is started. The indirect object's `victim_ejection_msg` verb is invoked, and the returned result printed to
the victim. The string returned by the indirect object's `ejection_msg` is printed to the player doing the ejecting.
The result returned by the indirect object's `oejection_msg` verb is printed to everyone else in the room.

Finally, the indirect object's `eject` verb is called to remove the victim.
"""

from moo.bootstrap.default_verbs import player
from moo.core import context

parser = context.parser
player = context.player
if parser.has_pobj("from"):
    container = parser.get_pobj("from")
    victims = container.find(parser.get_dobj_str())
    if not victims:
        print(f"Couldn't find {parser.get_dobj_str()} in {container.name}.")
    else:
        victim = victims.first()
        victim.tell(container.victim_ejection_msg())
        print(container.ejection_msg())
        container.announce(container.oejection_msg(), exclude=[player, victim])
        container.eject(victim)
else:
    victim = parser.get_dobj()
    victim.tell(victim.location.victim_ejection_msg())
