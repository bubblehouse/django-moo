#!moo verb on_player_action --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Overridable hook (spec 200, item C): a lightweight signal emitted *after* a
player successfully completes a common action.  Called as
``player.on_player_action(player, action, data)`` from ``default``'s player
verbs (``take``, ``drop``, ``give`` — movement/``visit`` is already covered by
``enterfunc``).

The default is a no-op: quest, achievement, tutorial, and analytics systems
override or observe it without each having to patch the core verbs.  ``action``
is a short string (``"take"``, ``"drop"``, ``"give"``); ``data`` is a small
dict of context (e.g. ``{"object": <pk>}``).
"""

return
