#!moo verb @rename --on $builder --dspec any --ispec to:any --ispec as:any

# pylint: disable=return-outside-function,undefined-variable

"""
Rename an object.

Usage:
    @rename <object> to <new-name>
    @rename <object> as <new-name>

The player must be allowed to `write` the object, which owners and wizards
are unless a rule denies it. Verb names are not affected by this command.
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
# This verb runs as its Wizard owner, so it checks the player who typed it, ACL rules included.
if not context.player.is_allowed("write", obj):
    print("Permission denied.")
    return
old_name = obj.title()
# set_name lets a class refuse a name; it raises UserError for a name that is taken or not allowed.
if obj.set_name(new_name) is False:
    print("Permission denied.")
    return
print(f"Renamed {old_name} to {new_name}.")
