#!moo verb trigger --on $daemon

# pylint: disable=return-outside-function,undefined-variable

"""
Fire one full tick (bookkeeping + ``on_tick``) synchronously, for testing.
Does not touch the scheduled ``PeriodicTask`` — the daemon's regular
schedule continues unchanged.
"""

return this.tick()
