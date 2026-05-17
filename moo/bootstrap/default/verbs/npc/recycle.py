#!moo verb recycle --on $npc

# pylint: disable=return-outside-function,undefined-variable

"""
Called by :func:`Object.delete` just before this NPC is removed. Drops the
anonymous ``Player`` row associated with this avatar, then calls
``this.disable()`` to cancel the scheduled ``PeriodicTask``.

``passthrough()`` would resolve to ``$root_class.recycle`` (a no-op) by way
of the ``$player`` branch — it walks ``$npc.parents.all()`` in storage order
and never reaches the ``$daemon`` side — so the disable call is explicit.
"""

from moo.sdk import remove_player_record

remove_player_record(this)
this.disable()
