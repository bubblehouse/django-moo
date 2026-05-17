#!moo verb @daemon --on $wizard --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Manage scheduled daemons.

Usage:
    @daemon list                 — show all $daemon descendants
    @daemon enable <name|pk>     — start scheduled ticks for <daemon>
    @daemon disable <name|pk>    — stop scheduled ticks
    @daemon trigger <name|pk>    — fire on_tick once, now (synchronous)
    @daemon kill <name|pk>       — disable and recycle the daemon Object
"""

from moo.sdk import context, lookup, get_scheduled_task_info, NoSuchObjectError

if not context.player.is_wizard():
    print("Permission denied.")
    return

parser = context.parser
if not parser.has_dobj_str():
    print("Usage: @daemon list|enable|disable|trigger|kill [<name|pk>]")
    return

parts = parser.get_dobj_str().split(maxsplit=1)
sub = parts[0].lower()
arg = parts[1] if len(parts) > 1 else None

daemon_class = lookup("Generic Daemon")

if sub == "list":
    rows = list(daemon_class.get_descendents().exclude(pk=daemon_class.pk))
    if not rows:
        print("No daemons.")
        return
    print(f"{'PK':>4}  {'Name':<24}  {'Interval':>8}  {'Runs':>6}  {'Last Tick':<24}  Target  Status")
    for d in rows:
        # Runs / last_tick come from daemon properties (updated by the tick
        # wrapper verb in real time). The PT is consulted only to determine
        # enabled / orphan / disabled status — PT counters lag because
        # django-celery-beat syncs them back to the DB only periodically.
        runs = str(d.get_property("tick_count") or 0)
        last_tick = d.get_property("last_tick_at") or "never"
        interval_s = d.get_property("interval") or 60
        pt_id = d.get_property("periodic_task_id")
        if pt_id is None:
            status = "disabled"
        else:
            info = get_scheduled_task_info(pt_id)
            if info is None:
                status = "orphan"
            else:
                status = "enabled" if info["enabled"] else "off"
        target = d.get_property("target")
        target_name = target.name if target else "-"
        print(
            f"  #{d.pk:<3}  {d.name[:24]:<24}  {str(interval_s):>8}  {runs:>6}  {last_tick:<24}  {target_name:<12}  {status}"
        )
    return

if arg is None:
    print(f"Usage: @daemon {sub} <name|pk>")
    return

try:
    obj = lookup(arg)
except NoSuchObjectError:
    print(f"No such object: {arg!r}")
    return

if not obj.is_a(daemon_class):
    print(f"{obj.name} is not a $daemon.")
    return

if sub == "enable":
    obj.enable()
elif sub == "disable":
    obj.disable()
elif sub == "trigger":
    obj.trigger()
    print(f"Triggered {obj.name}.")
elif sub == "kill":
    name = obj.title()
    obj.delete()
    print(f"Recycled {name}.")
else:
    print(f"Unknown subcommand {sub!r}. Try: list, enable, disable, trigger, kill.")
