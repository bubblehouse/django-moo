#!moo verb say --on $npc

# pylint: disable=return-outside-function,undefined-variable

"""
NPC-side speech helper. Method-style verb: call as ``npc.say("hello")``
from inside ``act`` (or any other verb owning the NPC's perspective).

Announces ``<NPC name>: <message>`` to every other occupant of the NPC's
current room. Returns silently if the NPC is in the void.

The parser ``say`` command lives on ``$room`` with ``--dspec any`` and won't
collide — that one is found via the player's location during command
dispatch, while this one is only reachable via direct method call on an
``$npc`` instance.
"""

if not args:
    return
message = args[0]
room = this.location
if room is None:
    return
room.announce_all_but(this, f"{this.name}: {message}")
