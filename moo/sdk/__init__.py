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
    prefetch_property,
    owned_objects,
    owned_objects_by_pks,
)
from .output import (
    write,
    open_editor,
    open_paginator,
    open_input,
    get_session_setting,
    set_session_setting,
    get_wrap_column,
    get_client_mode,
    can_open_editor,
    boot_player,
    send_oob,
    send_gmcp,
    room_info_payload,
    play_sound,
)
from .tasks import (
    invoke,
    set_task_perms,
    task_time_low,
    schedule_continuation,
    moo_eval,
)
from .ssh_keys import list_ssh_keys, add_ssh_key, remove_ssh_key
from .password import set_password
from .admin import server_info
from .mail import (
    send_message,
    get_mailbox,
    get_message,
    mark_read,
    delete_message,
    undelete_message,
    count_unread,
    get_mail_stats,
)

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

PLACEMENT_PREPS = ["on", "under", "behind", "before", "beside", "over"]

DIRECTIONS = [
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
    "up",
    "down",
]

OPPOSITE_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "up": "down",
    "down": "up",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
    "ne": "sw",
    "sw": "ne",
    "nw": "se",
    "se": "nw",
}

# Long direction names → IRE-style short codes for GMCP Room.Info payloads.
# Mudlet's generic mapper, MUSHclient mappers, and the Achaea/Aardwolf
# protocol convention all key on these. Unknown direction names round-trip
# unchanged so non-cardinal exits ("ladder up", "portal") still appear.
DIRECTION_SHORTCODES = {
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "northeast": "ne",
    "northwest": "nw",
    "southeast": "se",
    "southwest": "sw",
    "up": "u",
    "down": "d",
    "in": "in",
    "out": "out",
}

__all__ = [
    "lookup",
    "create",
    "players",
    "connected_players",
    "prefetch_property",
    "write",
    "open_editor",
    "open_paginator",
    "invoke",
    "set_task_perms",
    "context",
    "moojson",
    "get_session_setting",
    "set_session_setting",
    "get_client_mode",
    "can_open_editor",
    "send_oob",
    "send_gmcp",
    "room_info_payload",
    "play_sound",
    "list_ssh_keys",
    "add_ssh_key",
    "remove_ssh_key",
    "set_password",
    "open_input",
    "owned_objects",
    "owned_objects_by_pks",
    "task_time_low",
    "schedule_continuation",
    "server_info",
    "send_message",
    "get_mailbox",
    "get_message",
    "mark_read",
    "delete_message",
    "undelete_message",
    "count_unread",
    "get_mail_stats",
    "PLACEMENT_PREPS",
    "DIRECTIONS",
    "OPPOSITE_DIRECTIONS",
    "DIRECTION_SHORTCODES",
    "NoSuchObjectError",
    "NoSuchVerbError",
    "NoSuchPropertyError",
    "AmbiguousObjectError",
    "UserError",
    "UsageError",
    "AccessError",
]
