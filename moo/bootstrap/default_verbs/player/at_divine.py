#!moo verb @divine --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Consult the aether for a random sample of world objects by subject.

Usage:
    @divine location   — surface five rooms from the wider world
"""

import random
from moo.sdk import context, lookup

subject = (context.parser.get_dobj_str() or "").strip().lower()

if not subject:
    print("Divine what? Try: @divine location")
    return

system = lookup(1)

if subject == "location":
    parent = system.room
    all_objects = [obj for obj in parent.get_descendents() if obj.pk != parent.pk]

    if not all_objects:
        print("The aether is silent. No locations can be found.")
        return

    count = random.randint(3, 7)
    sample = random.sample(all_objects, min(count, len(all_objects)))
    lines = [f"Impressions surface from the noise of the world ({len(sample)}):"]
    for obj in sample:
        lines.append(f"  {obj.name} (#{obj.pk})")
    print("\n".join(lines))

else:
    print(f"The aether has no answer for '{subject}'.")
