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


def _publish_to_player(obj, message):
    """
    Publish a message directly to a player's Kombu queue without a permission check.
    This is an internal primitive used by `write()` and the async task writer.

    :param obj: the Object (player avatar) to write to
    :param message: any pickle-able object
    """
    from .models.auth import Player
    from kombu import Exchange, Queue
    from ..celery import app

    if isinstance(message, dict) and "event" in message:
        tracked = ContextManager.get("published_events")
        if isinstance(tracked, list):
            tracked.append(message["event"])
    if app.conf.broker_url == "memory://":
        warnings.warn(RuntimeWarning(f"ConnectionError({obj}): {message}"))
        return
    matching_players = Player.objects.filter(avatar=obj)
    caller = ContextManager.get("caller")
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
                dict(message=message, caller_id=caller.pk if caller else None),
                serializer="moojson",
                exchange=queue.exchange,
                routing_key=f"user-{player.user.pk}",
                declare=[queue],
                retry=True,
            )
