#!moo verb disable --on $daemon

# pylint: disable=return-outside-function,undefined-variable

"""
Stop this daemon: delete its ``PeriodicTask`` and clear the pointer.
Idempotent — calling on an already-disabled daemon is a no-op.
"""

from moo.sdk import cancel_scheduled_task, context

if not context.player.is_wizard():
    print("Permission denied.")
    return

pk = this.get_property("periodic_task_id")
if pk is None:
    print(f"{this.title()} is not enabled.")
    return

cancel_scheduled_task(pk)
this.set_property("periodic_task_id", None)
print(f"{this.title()} disabled.")
