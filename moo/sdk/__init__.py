# -*- coding: utf-8 -*-
"""
Public SDK for verb authors. Import game primitives from here:

    from moo.sdk import context, lookup, create, NoSuchObjectError
"""

from .context import context
from .objects import (
    lookup,
    create,
    players,
    connected_players,
    owned_objects,
    owned_objects_by_pks,
)
from .output import (
    write,
    open_editor,
    open_paginator,
    get_session_setting,
    set_session_setting,
    boot_player,
)
from .tasks import (
    invoke,
    set_task_perms,
    task_time_low,
    schedule_continuation,
    moo_eval,
)
from .ssh_keys import list_ssh_keys, add_ssh_key, remove_ssh_key
from .admin import server_info

# Re-export moojson for verb use
from ..core import moojson

from ..core.exceptions import (
    QuotaError,
    AmbiguousObjectError,
    UserError,
    UsageError,
    NoSuchObjectError,
    NoSuchVerbError,
    NoSuchPropertyError,
    AccessError,
)

__all__ = [
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
    "moojson",
    "get_session_setting",
    "set_session_setting",
    "list_ssh_keys",
    "add_ssh_key",
    "remove_ssh_key",
    "owned_objects",
    "owned_objects_by_pks",
    "task_time_low",
    "schedule_continuation",
    "server_info",
    "NoSuchObjectError",
    "NoSuchVerbError",
    "NoSuchPropertyError",
    "AmbiguousObjectError",
    "UserError",
    "UsageError",
    "AccessError",
]
