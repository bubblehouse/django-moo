#!moo verb english_list --on $string_utils

# pylint: disable=return-outside-function,undefined-variable

"""
Format a list as a natural English enumeration.

Strings pass through unchanged. Items that are Objects (detected via the
Python-side `kind` attribute) render as their title, and non-player Objects
are prefixed with "a" or "an" as appropriate.

Usage (called as a method):
    string_utils.english_list(items)

Examples:
    english_list([])                    → ""
    english_list(["apple"])             → "apple"
    english_list(["apple", "pear"])     → "apple and pear"
    english_list(["a","b","c"])         → "a, b, and c"
    english_list([newspaper_obj])       → "a newspaper"
    english_list([orange_obj])          → "an orange"
    english_list([wizard_obj])          → "Wizard"
"""

items = args[0]
if not items:
    return ""

rendered = []
for item in items:
    if hasattr(item, "kind") and item.kind == "object":
        name = item.title()
        if item.is_player():
            rendered.append(name)
        else:
            article = "an" if name[:1].lower() in "aeiou" else "a"
            rendered.append(f"{article} {name}")
    else:
        rendered.append(str(item))

if len(rendered) == 1:
    return rendered[0]
if len(rendered) == 2:
    return f"{rendered[0]} and {rendered[1]}"
return ", ".join(rendered[:-1]) + f", and {rendered[-1]}"
