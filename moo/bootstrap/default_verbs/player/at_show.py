#!moo verb @s*how --on $player --dspec any --ispec on:any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to examine other objects in detail. It returns details of an object's `owner`,
`location`, `parents`, and all the verbs and properties defined for the object, along with their values,
if permissions allow.
"""

from moo.sdk import context, open_paginator

parser = context.parser
player = context.player
if not parser.has_pobj_str("on"):
    obj = parser.get_dobj()
else:
    target = parser.get_pobj("on", lookup=True)
    name = parser.get_dobj_str()
    obj = None
    try:
        obj = target.get_verb(name, recurse=True)
    except Exception:  # pylint: disable=broad-except
        pass
    try:
        obj = target.get_property(name, recurse=True)
    except Exception:  # pylint: disable=broad-except
        pass
    if obj is None:
        print(f"Couldn't find a verb or property named '{name}' on {target}.")
        return

if obj.kind == "verb":
    open_paginator(context.player, obj.code, content_type="python")
    return
elif obj.kind == "property":
    open_paginator(context.player, obj.value, content_type="json")
    return

print(f"Details for {obj}:")
print(f"  Owner: {obj.owner}")
print(f"  Location: {obj.location}")
print(f"  Parents: {', '.join(str(p) for p in obj.parents.all())}")
print("  Verbs:")
for verb in obj.verbs.prefetch_related("names").select_related("owner").all():
    if player.is_allowed("execute", verb):
        print(f"    {', '.join(sorted(vn.name for vn in verb.names.all()))}")
print("  Properties:")
for prop in obj.properties.select_related("owner").all():
    if player.is_allowed("read", prop):
        print(f"    {prop.name}: {prop.value}")
