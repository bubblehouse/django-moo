# -*- coding: utf-8 -*-
"""
Per-account broadcast flood limiting (spec 200, item F).

RestrictedPython here uses a plain iterator and the only runaway backstop is the
Celery wall-clock kill — neither bounds a verb that spams everyone present
within the time budget (the ``$spew`` problem).  This module is that limiter: a
fixed-window counter, keyed to the *initiating* account, that bounds outbound
broadcast lines (messages an account causes to be sent to **other** players).  A
player's own output is never counted, so a long room description or a verbose
NPC is never clipped — the target is flooding, not verbosity.

The limit and window default to :data:`settings.MOO_BROADCAST_RATE_LIMIT` /
``MOO_BROADCAST_RATE_WINDOW`` and may be overridden at runtime by the System
Object properties ``broadcast_rate_limit`` / ``broadcast_rate_window`` (the
"sys knob").
"""

from django.conf import settings as _settings
from django.core.cache import cache


def _knob(name, default):
    """Read a System Object tuning property, falling back to ``default``.

    Reading the knob must never break the output path, so any error (missing
    System Object, no property, no context) falls back silently.
    """
    try:
        from ..core.models import Object  # pylint: disable=import-outside-toplevel

        sys_obj = Object.global_objects.filter(pk=1).first()
        if sys_obj is not None:
            value = sys_obj.get_property(name, recurse=False)
            if value is not None:
                return value
    except Exception:  # pylint: disable=broad-except
        pass
    return default


def broadcast_limit() -> int:
    """The effective per-window broadcast line budget (0 disables)."""
    return int(_knob("broadcast_rate_limit", getattr(_settings, "MOO_BROADCAST_RATE_LIMIT", 0)))


def broadcast_window() -> int:
    """The effective sliding-window length in seconds."""
    return max(1, int(_knob("broadcast_rate_window", getattr(_settings, "MOO_BROADCAST_RATE_WINDOW", 10))))


def broadcast_allowed(account_id) -> bool:
    """Charge one broadcast line to ``account_id`` and report whether it is allowed.

    Returns ``True`` (and does not charge) when the limit is disabled or no
    account is known.  Otherwise increments the account's fixed-window counter
    and returns ``False`` once the budget is exceeded.

    :param account_id: the initiating Player account id
    :return: True if the line may be sent, False if the account is over budget
    """
    limit = broadcast_limit()
    if limit <= 0 or account_id is None:
        return True
    window = broadcast_window()
    key = f"moo:ratelimit:broadcast:{account_id}"
    try:
        count = cache.incr(key)
    except ValueError:
        # Key absent/expired: start a fresh window.
        cache.set(key, 1, timeout=window)
        count = 1
    return count <= limit
