#!moo verb match_string --on $string_utils

# pylint: disable=return-outside-function,undefined-variable

"""
Prefix-match a query string against a list of candidate strings.

Usage (called as a method):
    string_utils.match_string(query, candidates)

Returns all items from ``candidates`` whose lowercased form starts with
the lowercased ``query``. Returns an empty list if nothing matches.

Examples:
    match_string("sw", ["sword", "shield", "axe"])  → ["sword"]
    match_string("s",  ["sword", "shield", "axe"])  → ["sword", "shield"]
    match_string("z",  ["sword", "shield"])          → []
"""

query = args[0].lower()
candidates = args[1]
return [c for c in candidates if str(c).lower().startswith(query)]
