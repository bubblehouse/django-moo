#!moo verb take --on $thing --dspec this --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
One or the other of these verbs is invoked when a player tries to take possession of an object i.e., pick it up. The
code involved is fairly straightforward. It checks to see if the player already has the object, and prints a suitable
message if this is the case. If not, then the `moveto` verb on the object is invoked. If this results in the object
moving into the player's inventory, then the take_succeeded messages defined on the object are printed. If the `moveto`
failed, then the `*take_failed` messages for the object are printed.

This scheme allows you to add extra conditions to restrict whether a player can take an object or not. For example, you
may place a notion of strength onto a player, and add weight to objects. If an object is too heavy for a player to lift,
then the object cannot be taken by the player. This sort of condition should be added to the `take` verb for the object
"""

from moo.sdk import context, NoSuchObjectError

# If "from <target>" was given, verify the object is actually placed on/near that target.
if context.parser.has_pobj_str("from"):
    try:
        from_target = context.parser.get_pobj("from")
        placement = this.placement
        if placement is None or placement[1] != from_target:
            tname = context.parser.get_pobj_str("from")
            print(f"{this.title()} isn't on the {tname}.")
            return
    except NoSuchObjectError:
        tname = context.parser.get_pobj_str("from")
        print(f"There is no '{tname}' here.")
        return

title = this.title()
if this.location == context.player:
    print(f"You already have {title} in your inventory.")
elif this.moveto(context.player):
    this.clear_placement()
    print(this.take_succeeded_msg(title))
    if msg := this.otake_succeeded_msg(title):
        this.location.announce(msg)
else:
    print(this.take_failed_msg(title))
    if msg := this.otake_failed_msg(title):
        this.location.announce(msg)
