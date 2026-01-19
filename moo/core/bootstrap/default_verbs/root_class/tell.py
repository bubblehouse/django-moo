#!moo verb tell --on "Root Class"

"""
This verb is used to send a message from one object to another. The `$root_class` definition of this verb tests to see
if the object is a player, and if it is, uses the `write()` primitive to print the argument list on the player's screen,
if they are connected. However, this verb can be overridden to allow arbitrary objects to pass messages between each
other, or to augment the way the message is handled.

One simple example is that of an object that listens to everything that happens in a room. Every verb that needs to
send text to players uses the `tell` verb. If an object has its own `tell` verb, it too will be able to act upon the
messages sent between objects in a room.

The `$player` class overrides this verb to filter messages in two different ways, as show below:

if (typeof(this.gaglist) != LIST || !(player in this.gaglist))
    if (player != this and this.paranoid == 1)
        pass("<", player.name, "(", player, ")> ", @args);
    else
        pass(@args);
    endif
endif

Firstly, if the message comes from a player that we don't want to listen to - the player has been gagged - then the
message is thrown away. Secondly, if the player is being paranoid, and the message is not from ourselves, it is
prefaced with the name of the originating object. The pass primitive is used to allow the :tell verb of the parent
class to send the message after it has been modified.
"""

from moo.core import api, write

if this.is_player():
    for arg in args:
        write(this, arg)
