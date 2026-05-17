#!moo verb enable --on $daemon

# pylint: disable=return-outside-function,undefined-variable

"""
Schedule this daemon to fire its ``on_tick`` verb every ``this.interval``
seconds, by creating a ``django_celery_beat.PeriodicTask``.

If the daemon already has a ``periodic_task_id`` pointing at a live PT,
this verb is a no-op. If the pointer is stale (PT deleted out-of-band),
a fresh PT is created and the pointer updated.

Wizard-only via the security gate in :func:`moo.sdk.invoke`.
"""

from moo.sdk import context, invoke, get_scheduled_task_info

if not context.player.is_wizard():
    print("Permission denied.")
    return

existing_pk = this.get_property("periodic_task_id")
if existing_pk:
    info = get_scheduled_task_info(existing_pk)
    if info is not None:
        print(f"{this.title()} is already enabled (interval={info['interval_seconds']}s).")
        return
    # stale pointer; fall through and create a fresh PT

interval = this.get_property("interval") or 60
pt = invoke(
    verb=this.get_verb("tick"),
    periodic=True,
    delay=interval,
)
this.set_property("periodic_task_id", pt.pk)
print(f"{this.title()} enabled (interval={interval}s).")
