#!moo verb on_tick --on $daemon

# pylint: disable=return-outside-function,undefined-variable

"""
Base daemon tick. A no-op stub that subclasses override.

The default body prints a debug line to the background log. User-facing
output should be emitted by an override using ``this.target.tell(...)``.

The base implementation does not increment any counter or set a timestamp —
those statistics live on the underlying ``PeriodicTask`` row
(``total_run_count``, ``last_run_at``) and are surfaced by ``@daemon list``.
"""

print(f"$daemon tick on {this.title()}.")
