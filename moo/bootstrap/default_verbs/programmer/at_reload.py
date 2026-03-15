#!moo verb @reload --on $programmer --dspec any --ispec on:any

# pylint: disable=return-outside-function,undefined-variable

"""

Reload filesystem-resident verbs.

Usage:
  @reload <verb-name> on <object>  — reload a single named verb on an object
  @reload <object-name>            — reload all filesystem verbs on an object
  @reload all                      — reload all filesystem verbs
"""

from moo.core.models import Verb
from moo.sdk import context, NoSuchVerbError, NoSuchObjectError

if context.parser.has_pobj_str("on"):
    verb_name = context.parser.get_dobj_str()
    target = context.parser.get_pobj("on", lookup=True)
    try:
        verb = target.get_verb(verb_name)
    except NoSuchVerbError:
        return
    if not context.player.is_wizard() and not context.player.owns(verb):
        print("Permission denied.")
        return
    verb.reload()
else:
    dobj_str = context.parser.get_dobj_str()
    if dobj_str == "all":
        if not context.player.is_wizard():
            print("Permission denied.")
            return
        verbs = Verb.objects.filter(filename__isnull=False, repo__isnull=False).exclude(filename="")
        count = 0
        errors = []
        for verb in verbs:
            print(f"  Reloading {verb}...")
            try:
                verb.reload()
                count += 1
            except Exception as e:  # pylint: disable=broad-except
                errors.append(f"  {verb}: {e}")
        print(f"Reloaded {count} verb(s).")
        for err in errors:
            print(err)
    else:
        try:
            target = context.parser.get_dobj(lookup=True)
        except NoSuchObjectError:
            print(f"I don't see {dobj_str} here.")
            return
        if not context.player.is_wizard() and not context.player.owns(target):
            print("Permission denied.")
            return
        verbs = Verb.objects.filter(origin=target, filename__isnull=False, repo__isnull=False).exclude(filename="")
        count = 0
        errors = []
        for verb in verbs:
            print(f"  Reloading {verb}...")
            try:
                verb.reload()
                count += 1
            except Exception as e:  # pylint: disable=broad-except
                errors.append(f"  {verb}: {e}")
        print(f"Reloaded {count} verb(s) on {target.name}.")
        for err in errors:
            print(err)
