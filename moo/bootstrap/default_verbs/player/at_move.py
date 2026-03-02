#!moo verb @move --on $player --dspec any --ispec to:any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to move objects from one location to another. The direct and indirect object strings are
used to match an object and location to move to. The `moveto` verb on the direct object is invoked to move it to the
indirect object location. If the location changes, and the object is a player, then the message

    blip disappears suddenly for parts unknown.

is displayed in the player's location before the move took place. Similarly, at the new location, the message

    blip materializes out of thin air.

is printed to the objects in the destination room. No messages are printed if an object is moved. If a permission
problem is found, it is reported to the player who typed the command.
"""

from moo.core import context, lookup

parser = context.parser
obj = parser.get_dobj()
destination = lookup(parser.get_pobj_str("to"))
if obj.is_player():
    obj.announce(_.sprintf("%D disappears suddenly for parts %i(to)."))
obj.moveto(destination)
if obj.is_player():
    destination.announce(_.sprintf("%D materializes out of thin air in %i(to)."))
