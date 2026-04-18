#!moo verb @rename --on $builder --dspec any --ispec to:any

# pylint: disable=return-outside-function,undefined-variable

"""
Rename an object.

Usage:
    @rename <object> to <new-name>

The caller must own the object or be a wizard. Verb names are not
affected by this command.
"""

from moo.sdk import context, UsageError

obj = context.parser.get_dobj(lookup=True)
if not context.parser.has_pobj_str("to"):
    raise UsageError(f"Usage: {verb_name} <object> to <new-name>")
new_name = context.parser.get_pobj_str("to")
if not new_name:
    raise UsageError("New name cannot be empty.")
if not (context.player.is_wizard() or obj.owner == context.player):
    print("Permission denied.")
    return
old_name = obj.title()
obj.name = new_name
obj.save()
print(f"Renamed {old_name} to {new_name}.")
