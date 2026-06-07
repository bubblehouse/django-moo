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

    #: The Object whose verb code is currently executing. Shifts as
    #: verbs invoke other verbs. Permission checks evaluate against
    #: this, not :attr:`player`.
    caller = descriptor("caller")
    #: The Object that originated the command. Stays anchored to the
    #: session initiator across nested verb calls. Use this for "who is
    #: acting" logic.
    player = descriptor("player")
    #: Callable that ``print()`` ends up calling. Sends a single string
    #: to the originating player's connection.
    writer = descriptor("writer")
    #: The :class:`Parser` for the current command. ``None`` when a
    #: Celery task re-invokes a verb without an active player command
    #: (e.g. scheduled :func:`invoke` calls).
    parser = descriptor("parser")
    #: The Celery task ID for the current execution.
    task_id = descriptor("task_id")
    #: ``TaskTime(elapsed, time_limit, remaining)`` namedtuple in
    #: seconds. ``None`` when no time limit is configured. Used for
    #: time-aware continuation.
    task_time = descriptor("task_time")
    #: Stack of caller frames accumulated as verbs invoke sub-verbs.
    #: The returned list is a copy; mutating it does not affect the
    #: live stack.
    caller_stack = descriptor("caller_stack")
    #: Per-task scratch dict for transient state shared across the verb
    #: calls within one command/invocation and never persisted. The
    #: attribute is read-only, but the returned dict is mutable — namespace
    #: your own keys (e.g. ``context.scratch.setdefault("myfeature", {})``).
    #: ``None`` outside an active session.
    scratch = descriptor("scratch")


context = _Context()


def invoked_verb_name(default: str | None = None) -> str | None:
    """
    Return the verb name as the player typed it (lowercased), or ``default``
    when there is no active parser context.

    Verbs called via :func:`moo.sdk.invoke`, async callbacks, or test
    harnesses have no parser; pass the sandbox-injected ``verb_name`` as
    ``default`` to fall back to the verb's defined name.
    """
    parser = context.parser
    if parser is None or not parser.words:
        return default
    return parser.words[0].lower()
