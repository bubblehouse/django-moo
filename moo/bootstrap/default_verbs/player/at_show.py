#!moo verb @s*how --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to examine other objects in detail. It returns details of an object's `owner`,
`location`, `parents`, and all the verbs and properties defined for the object, along with their values,
if permissions allow.
"""

from moo.core import context

parser = context.parser
player = context.player
obj = parser.get_dobj()

print(f"Details for {obj}:")
print(f"  Owner: {obj.owner}")
print(f"  Location: {obj.location}")
print(f"  Parents: {', '.join(str(p) for p in obj.parents.all())}")
print("  Verbs:")
for verb in obj.verbs.prefetch_related('names').select_related('owner').all():
    if player.is_allowed("execute", verb):
        print(f"    {', '.join(sorted(vn.name for vn in verb.names.all()))}")
print("  Properties:")
for prop in obj.properties.select_related('owner').all():
    if player.is_allowed("read", prop):
        print(f"    {prop.name}: {prop.value}")
