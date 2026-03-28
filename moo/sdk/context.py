# -*- coding: utf-8 -*-
"""
Context descriptor system.

Exposes ``context``, a singleton that provides read-only access to the
per-task context variables (caller, player, parser, etc.).
"""

from ..core.code import ContextManager as _ContextManager


class _Context:
    """
    This wrapper class makes it easy to use a number of contextvars.
    """

    class descriptor:
        """
        Used to perform dynamic lookups of contextvars.

        Defined as a data descriptor (implements both __get__ and __set__) so that
        Python's attribute lookup always invokes __get__ and never allows an instance
        attribute to shadow it.  Verb code must not be able to overwrite context.caller
        (or any other context attribute) with a forged object.
        """

        def __init__(self, name):
            self.name = name

        def __get__(self, obj, objtype=None):
            return _ContextManager.get(self.name)

        def __set__(self, obj, value):
            raise AttributeError("context attributes are read-only")

        def __delete__(self, obj):
            raise AttributeError("context attributes are read-only")

    def __setattr__(self, name, value):
        raise AttributeError("context attributes are read-only")

    caller = descriptor("caller")  # Code runs with the permission of this object
    player = descriptor("player")  # This object that originally invoked this session, defaults to original caller
    writer = descriptor("writer")  # A callable that will print to the player's console
    parser = descriptor("parser")
    task_id = descriptor("task_id")  # The current task ID
    task_time = descriptor("task_time")  # TaskTime(elapsed, time_limit, remaining) for the current task
    caller_stack = descriptor("caller_stack")  # A stack of callers, with the current caller at the end


context = _Context()
