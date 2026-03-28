#!moo verb english_list --on $string_utils

# pylint: disable=return-outside-function,undefined-variable

"""
Format a list as a natural English enumeration.

Usage (called as a method):
    string_utils.english_list(items)

Examples:
    english_list([])           → ""
    english_list(["a"])        → "a"
    english_list(["a", "b"])   → "a and b"
    english_list(["a","b","c"])→ "a, b, and c"
"""

items = args[0]
if not items:
    return ""
if len(items) == 1:
    return str(items[0])
if len(items) == 2:
    return f"{items[0]} and {items[1]}"
return ", ".join(str(i) for i in items[:-1]) + f", and {items[-1]}"
