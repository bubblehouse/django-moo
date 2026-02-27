#!moo verb gi*ve ha*nd --on $player  any --ispec to:any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to exchange objects between players. It performs a `moveto` on the direct object to
the inventory of the indirect object. If, after the move, the object is still in the possession of the donor, then it
is obvious that the recipient has rejected the gift. If this is the case, a suitable message is printed to the donor.
"""

from moo.core import context

player = context.player

if not context.parser.has_pobj_str("to"):
    print("Give to whom?")
    return

if not context.parser.has_dobj_str():
    print("What do you want to give?")
    return

recipient = context.parser.get_pobj("to")

if recipient == player:
    print("You can't give something to yourself.")
    return

gift = context.parser.get_dobj()

gift.moveto(recipient)
if gift.location != recipient:
    print(_.sprintf("%I doesn't want %d."))
else:
    print(_.sprintf("You give %d to %i."))
