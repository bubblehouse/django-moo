#!moo verb match_player --on $match_utils

# pylint: disable=return-outside-function,undefined-variable

"""
Prefix-match a name string against all player avatars.

Usage (called as a method):
    match_utils.match_player(query)

Returns a list of player Objects whose name starts with ``query``
(case-insensitive). Returns an empty list if nothing matches.

Uses ``players()`` (all players, not just connected ones). Call sites
that only want connected players should filter the result themselves.

Examples:
    match_player("Wiz")   → [<Wizard>]
    match_player("wiz")   → [<Wizard>]
    match_player("xyz")   → []
"""

from moo.sdk import players

query = args[0].lower()
return [p for p in players() if p.name.lower().startswith(query)]
