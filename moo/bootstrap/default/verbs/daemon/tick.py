#!moo verb tick --on $daemon

# pylint: disable=return-outside-function,undefined-variable

"""
Scheduler entry point. Wraps ``on_tick`` with bookkeeping that
``@daemon list`` reads in real time (the PeriodicTask's own
``total_run_count`` / ``last_run_at`` columns sync lazily and would
otherwise lag the display by minutes).

The :func:`moo.sdk.invoke` schedule created by ``enable`` targets this
verb, not ``on_tick`` — so subclasses can override ``on_tick`` cleanly
without worrying about bookkeeping.
"""

from datetime import datetime, timezone

count = this.get_property("tick_count") or 0
this.set_property("tick_count", count + 1)
this.set_property("last_tick_at", datetime.now(timezone.utc).isoformat())
return this.on_tick()
