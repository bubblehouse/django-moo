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

    if app.conf.broker_url == "memory://":
        warnings.warn(RuntimeWarning(f"ConnectionError({obj}): {message}"))
        return
    player = Player.objects.get(avatar=obj)
    # this is an uncommon scenario, but applies to the stock Player object if it hasn't been configured for login
    if not player.user:
        return
    with app.default_connection() as conn:
        channel = conn.channel()
        queue = Queue(
            f"messages.{player.user.pk}",
            Exchange("moo", type="direct", channel=channel),
            f"user-{player.user.pk}",
            channel=channel,
            auto_delete=True,
        )
        with app.producer_or_acquire() as producer:
            caller = ContextManager.get("caller")
            producer.publish(
                dict(message=message, caller_id=caller.pk if caller else None),
                serializer="moojson",
                exchange=queue.exchange,
                routing_key=f"user-{player.user.pk}",
                declare=[queue],
                retry=True,
            )
