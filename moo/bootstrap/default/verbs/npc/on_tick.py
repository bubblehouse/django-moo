#!moo verb on_tick --on $npc

# pylint: disable=return-outside-function,undefined-variable

"""
$daemon tick hook for NPCs. Forwards to ``this.act()`` — the personality
override point subclasses replace.

Bookkeeping (``tick_count``, ``last_tick_at``) still lives in the inherited
``$daemon.tick`` wrapper, so subclasses only need to think about behaviour.
"""

return this.act()
