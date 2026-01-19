#!moo verb recycle --on $room

"""
This verb is called by the LambdaMOO server when a room is recycled. When a room is recycled, something has to be done
with the room's contents, both players and objects, to stop them ending up in `$nothing`. This is done by trying to move
everything home.

The main loop goes through the complete contents list of the room. If the object is a player, then it is moved home,
using it's `moveto` verb, or to the `$player_start` room, using the `move()` primitive. All other objects are moved to the
inventories of their owners.

Note that if the attempt to move an object fails, then no action is taken. The server will place all objects still in
the room into `$nothing` when the room is recycled.
"""

for x in this.contents.all():
    if x.is_player():
        if x.has_property("home"):
            x.moveto(x.home)
        if x.location == this:
            x.location = _.player_start
            x.save()
    else:
        x.moveto(x.owner)

