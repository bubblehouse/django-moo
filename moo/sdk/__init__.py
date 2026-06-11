# -*- coding: utf-8 -*-
"""
Public SDK for verb authors. Import game primitives from here:

    from moo.sdk import context, lookup, create, NoSuchObjectError
"""

from .context import context, invoked_verb_name
from .objects import (
    lookup,
    create,
    players,
    connected_players,
    prefetch_property,
    owned_objects,
    owned_objects_by_pks,
    ensure_player_record,
    remove_player_record,
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
    cancel_scheduled_task,
    get_scheduled_task_info,
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


def direction_argument(parser=None, *, after_prep=None):
    """
    Recover a direction name from the parser, tolerating direction-as-preposition.

    Two of our direction words — ``up`` and ``down`` — are also registered
    prepositions.  Player input like ``@dig up to The Loft`` parses ``up``
    as a preposition with no indirect object, so the verb body's
    :func:`get_dobj_str` returns empty even though the player clearly typed
    a direction.  This helper checks the obvious slots in order:

    1. ``parser.get_pobj_str(after_prep)`` when ``after_prep`` is set and
       was matched with an indirect-object string (e.g. ``look through up``
       where the ``through`` prep captured ``"up"`` as iobj_str).
    2. ``parser.get_dobj_str()`` (the default direction-as-dobj path).
    3. Any registered direction that appears as a parsed preposition with
       no iobj (the ``up``/``down``-as-particle case).
    4. ``parser.words[1]`` when ``after_prep`` is None; or the word
       immediately following ``after_prep`` in ``parser.words`` otherwise.
       Used as a last-resort recovery.

    :param parser: Parser instance.  Defaults to :data:`context.parser`.
    :param after_prep: When set, look for the direction as the iobj or the
        word following this preposition (e.g. ``"through"`` for
        ``look through up``).
    :returns: Lowercase direction string, or ``""`` if none recoverable.
    """
    if parser is None:
        from moo.sdk.context import context as _ctx  # pylint: disable=import-outside-toplevel,cyclic-import

        parser = _ctx.parser
    if parser is None:
        return ""
    if after_prep:
        candidate = parser.get_pobj_str(after_prep) if parser.has_pobj_str(after_prep) else ""
        if candidate:
            return candidate.lower()
    else:
        candidate = parser.get_dobj_str() if parser.has_dobj_str() else ""
        if candidate:
            return candidate.lower()
    # ``up``/``down`` may have been consumed as preps with no iobj.
    for direction in DIRECTIONS:
        if direction in parser.prepositions:
            return direction
    # Last resort — scan parser.words.
    words = list(parser.words or [])
    if after_prep and after_prep in (w.lower() for w in words):
        idx = next(i for i, w in enumerate(words) if w.lower() == after_prep)
        if idx + 1 < len(words):
            return words[idx + 1].lower()
    if not after_prep and len(words) > 1:
        return words[1].lower()
    return ""


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
    "cancel_scheduled_task",
    "get_scheduled_task_info",
    "set_task_perms",
    "moo_eval",
    "context",
    "invoked_verb_name",
    "moojson",
    "get_session_setting",
    "set_session_setting",
    "get_client_mode",
    "get_wrap_column",
    "can_open_editor",
    "boot_player",
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
    "ensure_player_record",
    "remove_player_record",
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
    "direction_argument",
    "DIRECTION_SHORTCODES",
    "NoSuchObjectError",
    "NoSuchVerbError",
    "NoSuchPropertyError",
    "AmbiguousObjectError",
    "UserError",
    "UsageError",
    "AccessError",
]
