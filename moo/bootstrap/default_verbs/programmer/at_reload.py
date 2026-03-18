#!moo verb @reload --on $programmer --dspec any --ispec on:any

# pylint: disable=return-outside-function,undefined-variable,redefined-outer-name

"""

Reload filesystem-resident verbs.

Usage:
  @reload <verb-name> on <object>  — reload a single named verb on an object
  @reload <object-name>            — reload all filesystem verbs on an object
  @reload all                      — reload all filesystem verbs
"""

from moo.core.models import Verb
from moo.sdk import context, invoke, NoSuchVerbError, NoSuchObjectError

TIME_THRESHOLD = 0.5


def reload_batch(verbs):
    count = 0
    for i, verb in enumerate(verbs):
        task_time = context.task_time
        if task_time and task_time.remaining is not None and task_time.remaining <= TIME_THRESHOLD:
            remaining_pks = [v.pk for v in verbs[i:]]
            reload_verb = context.parser.verb if context.parser else this.get_verb("@reload")
            invoke(remaining_pks, verb=reload_verb)
            context.player.tell(
                f"  Time limit approaching; continuing in a new task ({len(remaining_pks)} verb(s) remaining)..."
            )
            return True, count
        context.player.tell(f"  Reloading {verb}...")
        try:
            verb.reload()
            count += 1
        except Exception as e:  # pylint: disable=broad-except
            context.player.tell(f"  {verb}: {e}")
    return False, count


if args and isinstance(args[0], list):
    verbs = list(Verb.objects.filter(pk__in=args[0]))
    continued, count = reload_batch(verbs)
    if not continued:
        context.player.tell(f"Reloaded {count} verb(s).")
elif context.parser.has_pobj_str("on"):
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
        verbs = list(Verb.objects.filter(filename__isnull=False, repo__isnull=False).exclude(filename=""))
        continued, count = reload_batch(verbs)
        if not continued:
            context.player.tell(f"Reloaded {count} verb(s).")
    else:
        try:
            target = context.parser.get_dobj(lookup=True)
        except NoSuchObjectError:
            print(f"I don't see {dobj_str} here.")
            return
        if not context.player.is_wizard() and not context.player.owns(target):
            print("Permission denied.")
            return
        verbs = list(
            Verb.objects.filter(origin=target, filename__isnull=False, repo__isnull=False).exclude(filename="")
        )
        continued, count = reload_batch(verbs)
        if not continued:
            context.player.tell(f"Reloaded {count} verb(s) on {target.name}.")
