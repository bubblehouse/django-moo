#!moo verb table_get table_put --on "System Object"
# pylint: disable=return-outside-function,undefined-variable
"""
ZIL table primitives — pure list operations on the value passed in.

table_get:  args[0] = list, args[1] = index → list[index] (or None)
table_put:  args[0] = list, args[1] = index, args[2] = value (in-place)
"""

if verb_name == "table_get":
    table = args[0] if args else None
    idx = args[1] if len(args) > 1 else 0
    if table is None or not isinstance(table, list):
        return None
    if idx is None or idx < 0 or idx >= len(table):
        return None
    return table[idx]

if verb_name == "table_put":
    table = args[0] if args else None
    idx = args[1] if len(args) > 1 else 0
    val = args[2] if len(args) > 2 else None
    if table is None or not isinstance(table, list):
        return None
    if idx is None or idx < 0:
        return None
    while len(table) <= idx:
        table.append(0)
    table[idx] = val
    return val
