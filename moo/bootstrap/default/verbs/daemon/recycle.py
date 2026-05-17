#!moo verb recycle --on $daemon

# pylint: disable=return-outside-function,undefined-variable

"""
Called by :func:`Object.delete` just before the daemon Object is removed.
Disables the daemon so its scheduled ``PeriodicTask`` is cleaned up; the
Object itself is removed by the caller after this verb returns.
"""

this.disable()
