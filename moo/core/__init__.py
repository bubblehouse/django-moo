# -*- coding: utf-8 -*-
"""
Core MOO functionality, object model, verbs.

Public verb-author API has moved to ``moo.sdk``. This module re-exports
everything for backward compatibility with internal framework code.
"""

import logging
import warnings

# Re-export the public SDK so that internal framework files that do
# ``from moo.core import context, lookup, ...`` continue to work
# without modification.
from moo.sdk import (
    lookup,
    create,
    players,
    connected_players,
    write,
    open_editor,
    open_paginator,
    invoke,
    set_task_perms,
    context,
    NoSuchObjectError,
    NoSuchVerbError,
    NoSuchPropertyError,
    AmbiguousObjectError,
)

from .code import ContextManager

__all__ = [
    "_publish_to_player",
    "_build_envelope",
    "current_provenance",
    "lookup",
    "create",
    "players",
    "connected_players",
    "write",
    "open_editor",
    "open_paginator",
    "invoke",
    "set_task_perms",
    "context",
    "NoSuchObjectError",
    "NoSuchVerbError",
    "NoSuchPropertyError",
    "AmbiguousObjectError",
]

log = logging.getLogger(__name__)


def current_provenance():
    """Return the always-on provenance triple for the running task, server-side.

    The triple is ``{"origin", "verb", "owner"}`` taken from the top of the
    caller stack (spec 200, item E): ``origin`` is the object the running verb
    is acting on, ``verb`` the responsible verb name, and ``owner`` the pk of
    the verb's permission owner (its ``context.caller``).  All three are read
    from the in-memory caller stack — **no database query** — so attaching this
    to every outbound message stays a tag-and-id on the hot path.  Full
    caller-stack capture for a report/audit happens separately via
    :func:`moo.sdk.provenance.capture_provenance_stack`.

    Returns ``None`` outside an active task (no caller stack).
    """
    stack = ContextManager.get("caller_stack")
    if not stack:
        return None
    frame = stack[-1]
    this = frame.get("this")
    caller = frame.get("caller")
    return {
        "origin": this.pk if this is not None else None,
        "verb": frame.get("verb_name"),
        "owner": caller.pk if caller is not None else None,
    }


def _build_envelope(message, kind="text"):
    """Build the published Kombu envelope, attaching always-on provenance.

    Kept separate from the publish call so the envelope (and the provenance it
    carries) is unit-testable even under the ``memory://`` test broker, where
    the publish itself short-circuits.

    :param message: the payload (a plain string, or an OOB ``event`` dict)
    :param kind: the structural output tag (``text``/``say``/``emote``/
        ``system``/``persona``); the client renders by it so a user-authored
        line cannot present as a system line or another actor.
    """
    caller = ContextManager.get("caller")
    return dict(
        message=message,
        caller_id=caller.pk if caller else None,
        kind=kind,
        provenance=current_provenance(),
    )


def _publish_to_player(obj, message, kind="text"):
    """
    Publish a message directly to a player's Kombu queue without a permission check.
    This is an internal primitive used by `write()` and the async task writer.

    :param obj: the Object (player avatar) to write to
    :param message: any pickle-able object
    :param kind: structural output tag carried in the envelope (see
        :func:`_build_envelope`)
    """
    from .models.auth import Player
    from kombu import Exchange, Queue
    from django.conf import settings
    from ..celery import app

    if isinstance(message, dict) and "event" in message:
        tracked = ContextManager.get("published_events")
        if isinstance(tracked, list):
            tracked.append(message["event"])
    # F: drop broadcast text lines from an account that is over its flood budget.
    # Gated on the cheap settings flag so the common (disabled) path adds no DB
    # work; only text sent to *another* avatar is charged (self output is exempt).
    if isinstance(message, str) and getattr(settings, "MOO_BROADCAST_RATE_LIMIT", 0) > 0:
        initiator = ContextManager.get("player")
        if initiator is not None and getattr(obj, "pk", None) != initiator.pk:
            from ..sdk.ratelimit import broadcast_allowed
            from ..sdk.accounts import account_id_for

            if not broadcast_allowed(account_id_for(initiator)):
                return
    if app.conf.broker_url == "memory://":
        warnings.warn(RuntimeWarning(f"ConnectionError({obj}): {message}"))
        return
    envelope = _build_envelope(message, kind=kind)
    matching_players = Player.objects.filter(avatar=obj)
    # Use the producer's own pooled channel for both publishing and queue
    # declaration. The prior pattern allocated a separate channel via
    # ``app.default_connection().channel()`` for the Queue/Exchange binding,
    # but that connection came from a separate pool that could hand back a
    # stale (transport.connection is None) entry under sustained load —
    # ``conn.channel()`` then raised ``AttributeError: 'NoneType' object
    # has no attribute '_used_channel_ids'`` and every page/tell verb that
    # routed through here failed for the rest of the worker's life.
    # ``producer.publish(..., declare=[queue], retry=True)`` binds the
    # Queue/Exchange to the producer's channel at publish time and reconnects
    # on transport errors, so no separate channel allocation is needed.
    with app.producer_or_acquire() as producer:
        for player in matching_players:
            # this is an uncommon scenario, but applies to the stock Player object if it hasn't been configured for login
            if not player.user:
                continue
            queue = Queue(
                f"messages.{player.user.pk}",
                Exchange("moo", type="direct"),
                f"user-{player.user.pk}",
                auto_delete=True,
            )
            producer.publish(
                envelope,
                serializer="moojson",
                exchange=queue.exchange,
                routing_key=f"user-{player.user.pk}",
                declare=[queue],
                retry=True,
            )
