#!moo verb act --on $npc

# pylint: disable=return-outside-function,undefined-variable

"""
The personality hook for an NPC. The base implementation does nothing —
subclasses override this verb to decide whether to move, speak, attack, or
idle on each scheduled tick.

Called by ``$npc.on_tick``; not invoked directly by the parser.
"""
