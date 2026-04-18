#!moo verb @realm @classes --on $builder --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Display the inheritance tree rooted at an object.

Usage:
    @realm <object>     — show all descendants of <object>
    @realm              — same as @classes
    @classes            — show the full class hierarchy from $root_class

Each object is shown indented by its depth in the tree (2 spaces per level).
Output is sent to the paginator for large hierarchies.
"""

from moo.sdk import context, lookup, open_paginator, NoSuchObjectError

if context.parser.has_dobj_str():
    try:
        root = context.parser.get_dobj(lookup=True)
    except NoSuchObjectError:
        print(f"No object named '{context.parser.get_dobj_str()}' found.")
        return
else:
    system = lookup(1)
    root = system.root_class

descs = list(root.get_descendents())

lines = [f"{root.title()} (#{root.id})"]
if not descs:
    lines.append("  (no descendants)")
else:
    for obj in descs:
        indent = "  " * obj.depth
        lines.append(f"{indent}{obj.title()} (#{obj.id})")

open_paginator(context.player, "\n".join(lines), content_type="text")
