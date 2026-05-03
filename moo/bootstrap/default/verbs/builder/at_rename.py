#!moo verb @rename --on $builder --dspec any --ispec to:any --ispec as:any

# pylint: disable=return-outside-function,undefined-variable

"""
Rename an object.

Usage:
    @rename <object> to <new-name>
    @rename <object> as <new-name>

The caller must own the object or be a wizard. Verb names are not
affected by this command.
"""

from moo.sdk import context, UsageError

obj = context.parser.get_dobj()
if context.parser.has_pobj_str("to"):
    new_name = context.parser.get_pobj_str("to")
elif context.parser.has_pobj_str("as"):
    new_name = context.parser.get_pobj_str("as")
else:
    raise UsageError(f"Usage: {verb_name} <object> to|as <new-name>")
if not new_name:
    raise UsageError("New name cannot be empty.")
if not (context.player.is_wizard() or obj.owner == context.player):
    print("Permission denied.")
    return
old_name = obj.title()
obj.name = new_name
obj.save()
print(f"Renamed {old_name} to {new_name}.")
