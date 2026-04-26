#!moo verb @rmverb @delverb --on $programmer --dspec any --ispec on:any

# pylint: disable=return-outside-function,undefined-variable

"""
Remove a verb from an object.

Usage:
    @rmverb <verb-name> on <object>

The caller must own the verb (or be a wizard). Filesystem-backed verbs
loaded from a `default_verbs/` file can be removed; they will reappear on
the next `moo_init --sync` if the file is still present.
"""

from moo.sdk import context, NoSuchVerbError

target_verb_name = context.parser.get_dobj_str()
target = context.parser.get_pobj("on", lookup=True)

try:
    verb = target.get_verb(target_verb_name, recurse=False)
except NoSuchVerbError:
    print(f"No verb '{target_verb_name}' on {target}.")
    return

if not context.player.is_wizard() and not context.player.owns(verb):
    print("Permission denied.")
    return

verb.delete()
print(f"Removed verb {target_verb_name} from {target}.")
