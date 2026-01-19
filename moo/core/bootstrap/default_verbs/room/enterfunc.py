##!moo verb enterfunc --on $room

"""
This verb is invoked by the LambdaMOO server when an object moves into a room, as part of action of the `move` primitive.
The actions taken for a room are very straightforward. If `thing` is a player object, then we tell the player where s/he
has moved into using the `$room.look_self` verb on the room. If the object is the `blessed_object` for this room, then the
`blessed_object` property for the room is reset to None. For further details on blessed objects, refer to the
description of `$room.bless_for_entry`.
"""

thing = args[0]
if thing.is_player():
    thing.tell(this.look_self())

if thing == this.blessed_object:
    this.blessed_object = None
    this.save()
