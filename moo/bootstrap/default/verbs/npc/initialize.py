#!moo verb initialize --on $npc

# pylint: disable=return-outside-function,undefined-variable

"""
Called by :func:`moo.sdk.create` immediately after an NPC is created. Ensures
an anonymous ``Player`` row exists for this avatar so the parser treats it as
a player (``is_player() == True``) while leaving it unconnected
(``is_connected() == False`` — ``tell()`` silently drops with no warning).

The wizard ``@npc create`` command also calls ``ensure_player_record`` directly
so the record is in place by the time it returns; this hook is the safety net
for direct programmatic ``create()`` calls.
"""

from moo.sdk import ensure_player_record

ensure_player_record(this)
