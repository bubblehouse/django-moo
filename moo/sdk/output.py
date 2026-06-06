# -*- coding: utf-8 -*-
"""
Player I/O functions: write, editor, paginator, session settings, boot.
"""

from ..core.exceptions import UserError
from .context import context


def write(obj, message):
    """
    Send an asynchronous message to the user.

    :param obj: the Object to write to
    :type obj: Object
    :param message: any pickle-able object
    :type message: Any
    """
    from moo.core import _publish_to_player

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can write to the console.")
    _publish_to_player(obj, message)


def open_editor(obj, initial_content: str, callback_verb, *args, content_type: str = "text", title: str | None = None):
    """
    Request the connected SSH client to open a full-screen text editor.
    When the user saves, the edited text is passed to callback_verb as args[0],
    followed by any extra positional arguments supplied here.
    If the user cancels, the callback is not invoked.

    :param obj: the player Object whose client should open the editor
    :param initial_content: text to pre-populate the editor buffer
    :param callback_verb: Verb to invoke with the edited text as args[0]
    :param args: additional arguments forwarded to the callback verb as args[1:]
    :param content_type: "python", "json", or "text" (default); controls syntax highlighting
    """
    from moo.core import _publish_to_player

    if content_type not in ("python", "json", "text"):
        raise UserError(f"content_type must be 'python', 'json', or 'text', not {content_type!r}.")
    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can open the editor.")
    _publish_to_player(
        obj,
        {
            "event": "editor",
            "content": initial_content,
            "content_type": content_type,
            "title": title,
            "args": list(args),
            "callback_this_id": callback_verb._invoked_object.pk,  # pylint: disable=protected-access
            "callback_verb_name": callback_verb._invoked_name,  # pylint: disable=protected-access
            "caller_id": context.caller.pk,
            "player_id": (context.player or context.caller).pk,
        },
    )


def open_paginator(obj, content: str, content_type: str = "text"):
    """
    Request the connected SSH client to open a full-screen read-only paginator.
    The user can scroll through the content and press Q to quit.

    In raw-mode sessions (MUD clients, line-oriented terminals) the SSH server
    intercepts the paginator event and writes the content directly to the
    terminal instead of opening the interactive UI.

    :param obj: the player Object whose client should open the paginator
    :param content: text to display
    :param content_type: "python", "json", or "text" (default); controls syntax highlighting
    """
    from moo.core import _publish_to_player

    if content_type not in ("python", "json", "text"):
        raise UserError(f"content_type must be 'python', 'json', or 'text', not {content_type!r}.")
    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can open the paginator.")
    _publish_to_player(
        obj,
        {
            "event": "paginator",
            "content": content,
            "content_type": content_type,
        },
    )


def open_input(obj, prompt: str, callback_verb, *args, password: bool = False):
    """
    Request the connected SSH client to show an inline input prompt.
    When the user submits, the entered text is passed to callback_verb as args[0],
    followed by any extra positional arguments supplied here.
    If the user cancels (Ctrl-C / Ctrl-D), the callback is not invoked.

    :param obj: the player Object whose client should show the prompt
    :param prompt: text to display before the input field
    :param callback_verb: Verb to invoke with the entered text as args[0]
    :param args: additional arguments forwarded to the callback verb as args[1:]
    :param password: if True, input is hidden (no echo)
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can open an input prompt.")
    _publish_to_player(
        obj,
        {
            "event": "input_prompt",
            "prompt": prompt,
            "password": password,
            "args": list(args),
            "callback_this_id": callback_verb._invoked_object.pk,  # pylint: disable=protected-access
            "callback_verb_name": callback_verb._invoked_name,  # pylint: disable=protected-access
            "caller_id": context.caller.pk,
            "player_id": (context.player or context.caller).pk,
        },
    )


def _plain_text(markup: str) -> str:
    """Strip Rich markup to plain text (for GMCP payloads)."""
    from rich.text import Text  # pylint: disable=import-outside-toplevel

    try:
        return Text.from_markup(markup).plain
    except Exception:  # pylint: disable=broad-except
        return markup


def open_window(obj, *args, height: int = 1, title: str | None = None, callback_verb=None):
    """
    Switch the player's rich client into windowed display mode.

    Opens a persistent split-screen layout: a fixed top region of ``height``
    rows (painted with :func:`window_write`, or :func:`window_cursor` +
    :func:`window_emit`), a scrolling output region, and an input line.
    The session stays in window mode until :func:`close_window`, the player
    presses the close key, or they disconnect. Window mode is mutually
    exclusive with the editor and paginator.

    No-ops for non-rich clients. GMCP-capable clients (e.g. Mudlet) instead
    receive a ``Window.Open`` event so they can render a native status area.

    :param obj: the player Object whose client should enter window mode
    :param height: number of rows in the fixed top region
    :param title: optional title for the top region
    :param callback_verb: optional Verb invoked when the window closes, with
        the close reason as ``args[0]`` followed by any extra positional args
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can open a window.")
    player = context.player or context.caller
    _publish_to_player(
        obj,
        {
            "event": "window_open",
            "height": int(height),
            "title": title,
            "args": list(args),
            "callback_this_id": callback_verb._invoked_object.pk if callback_verb else None,  # pylint: disable=protected-access
            "callback_verb_name": callback_verb._invoked_name if callback_verb else None,  # pylint: disable=protected-access
            "caller_id": context.caller.pk if context.caller else None,
            "player_id": player.pk if player else None,
        },
    )
    send_gmcp(obj, "Window.Open", {"height": int(height), "title": title})


def window_write(obj, row: int, col: int, text: str):
    """
    Write ``text`` at grid position ``(row, col)`` in the top region.

    ``text`` may contain Rich markup. Equivalent to :func:`window_cursor`
    followed by :func:`window_emit`. No-ops for non-rich clients; GMCP
    clients receive a ``Window.Cell`` event.

    :param obj: the player Object whose window to paint
    :param row: zero-based row in the top region
    :param col: zero-based column in the top region
    :param text: Rich-markup text to place at ``(row, col)``
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can write to a window.")
    _publish_to_player(obj, {"event": "window_write", "row": int(row), "col": int(col), "text": str(text)})
    send_gmcp(obj, "Window.Cell", {"row": int(row), "col": int(col), "text": _plain_text(str(text))})


def window_cursor(obj, row: int, col: int):
    """
    Move the top-region cursor to ``(row, col)`` (for :func:`window_emit`).

    Mirrors the Z-machine ``set_cursor`` opcode. No-ops for non-rich clients;
    GMCP clients receive a ``Window.Cursor`` event.
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can move the window cursor.")
    _publish_to_player(obj, {"event": "window_cursor", "row": int(row), "col": int(col)})
    send_gmcp(obj, "Window.Cursor", {"row": int(row), "col": int(col)})


def window_emit(obj, text: str):
    """
    Write ``text`` at the current top-region cursor and advance it.

    The stateful companion to :func:`window_cursor`, used to translate a
    ``set_cursor`` + ``print`` sequence faithfully. ``text`` may contain Rich
    markup. No-ops for non-rich clients; GMCP clients receive a
    ``Window.Text`` event.
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can write to a window.")
    _publish_to_player(obj, {"event": "window_emit", "text": str(text)})
    send_gmcp(obj, "Window.Text", {"text": _plain_text(str(text))})


def window_clear(obj, row: int | None = None):
    """
    Clear the whole top region, or a single ``row`` when given.

    No-ops for non-rich clients; GMCP clients receive a ``Window.Clear`` event.
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can clear a window.")
    _publish_to_player(obj, {"event": "window_clear", "row": None if row is None else int(row)})
    send_gmcp(obj, "Window.Clear", {"row": None if row is None else int(row)})


def window_split(obj, height: int):
    """
    Set the top region to ``height`` rows (opening window mode if needed).

    Mirrors the Z-machine ``split_window`` opcode. No-ops for non-rich
    clients; GMCP clients receive a ``Window.Split`` event.
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can resize a window.")
    _publish_to_player(obj, {"event": "window_split", "height": int(height)})
    send_gmcp(obj, "Window.Split", {"height": int(height)})


def close_window(obj):
    """
    Leave windowed display mode and return to the normal scrolling shell.

    No-ops for non-rich clients; GMCP clients receive a ``Window.Close`` event.
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can close a window.")
    _publish_to_player(obj, {"event": "window_close"})
    send_gmcp(obj, "Window.Close", None)


def window_supported(obj=None) -> bool:
    """
    True if the current player's client can display a window (rich mode).

    Mirrors :func:`can_open_editor`'s rich-mode check. Raw / line-based MUD
    clients return ``False`` (window SDK calls no-op the full-screen UI for
    them, though GMCP-capable clients still receive ``Window.*`` events).

    :param obj: accepted for call-site symmetry; ignored (state is read from
        the current player's session).
    """
    return get_client_mode() == "rich"


def _player_user_pk(obj):
    """
    Resolve a player avatar Object to its Django User PK.

    Session settings are keyed by Django User PK in the SSH server's
    ``_session_settings`` registry and Django cache; SDK callers are given
    an avatar Object via ``context.player``, so we go through the
    :class:`Player` model to bridge namespaces.
    """
    from ..core.models.auth import Player  # pylint: disable=import-outside-toplevel

    if obj is None:
        return None
    player = Player.objects.filter(avatar=obj).select_related("user").first()
    if player is None or player.user is None:
        return None
    return player.user.pk


def get_session_setting(key, default=None):
    """
    Get a session-specific output setting for the current player.

    Session settings are stored per-user and cleared on disconnect.
    Used by PREFIX, SUFFIX, OUTPUTPREFIX/SUFFIX, and the ``a11y`` verb.

    Checks the in-process ``_session_settings`` dict first (authoritative in the
    SSH server process and in tests), then falls back to the Django cache so
    Celery workers — which run in a separate process — can also read the value.

    :param key: setting name ('output_prefix', 'output_suffix', 'quiet_mode', 'color_system')
    :param default: value to return if setting is not found
    :return: setting value or default
    """
    from django.core.cache import cache
    from ..shell import prompt as prompt_module

    user_pk = _player_user_pk(context.player)
    if user_pk is None:
        return default

    settings = prompt_module._session_settings.get(user_pk, {})  # pylint: disable=protected-access
    if key in settings:
        return settings[key]

    value = cache.get(f"moo:session:{user_pk}:{key}")
    return value if value is not None else default


def set_session_setting(key, value):
    """
    Set a session-specific output setting for the current player.

    Session settings are stored per-user and cleared on disconnect.
    Used by PREFIX, SUFFIX, OUTPUTPREFIX/SUFFIX, and the ``a11y`` verb.

    Writes to the Django cache (accessible cross-process from Celery workers)
    and also publishes a ``session_setting`` event to the player's Kombu queue
    so the SSH server's ``process_messages()`` loop can update its own registry.

    :param key: setting name ('output_prefix', 'output_suffix', 'quiet_mode', 'color_system')
    :param value: setting value
    """
    from django.core.cache import cache
    from moo.core import _publish_to_player

    player = context.player
    if not player:
        return

    user_pk = _player_user_pk(player)
    if user_pk is not None:
        cache.set(f"moo:session:{user_pk}:{key}", value, timeout=86400)

    _publish_to_player(player, {"event": "session_setting", "key": key, "value": value})


def get_wrap_column():
    """
    Return the effective wrap column for the current player.

    Reads the player's ``wrap_column`` property. If it is ``"auto"`` (or the
    property is not set), returns the ``terminal_width`` session setting,
    falling back to 80 if the terminal width is not known.
    """
    from ..core.exceptions import NoSuchPropertyError

    player = context.player
    wrap = "auto"
    if player:
        try:
            wrap = player.get_property("wrap_column")
        except NoSuchPropertyError:
            pass
    if wrap == "auto":
        return get_session_setting("terminal_width", 80)
    try:
        return int(wrap)
    except (ValueError, TypeError):
        return 80


def get_client_mode() -> str:
    """
    Return the current player's shell mode.

    Returns ``"rich"`` (prompt_toolkit TUI, the default) or ``"raw"`` (line-
    based I/O for traditional MUD clients that cannot handle cursor control).

    Verbs use this to short-circuit editor-opening code paths in raw mode and
    suggest the inline ``@edit ... with "..."`` form instead. Most verbs
    should call :func:`can_open_editor` instead, which also returns ``True``
    for raw-mode clients that advertise GMCP Editor support (e.g. the
    djangomoo Mudlet bridge).
    """
    return get_session_setting("mode", "rich")


def can_open_editor() -> bool:
    """
    True if the current player's client can display an editor.

    Either the player is in ``rich`` mode (prompt_toolkit TUI), or their
    client advertises support for the GMCP ``Editor`` package via
    ``Core.Supports.Set`` (the djangomoo Mudlet bridge does this; the
    server hands the edit off to the client's preferred local editor over
    GMCP). Verbs that open the editor should gate on this rather than
    ``get_client_mode() == "raw"`` so bridge-equipped MUD clients are not
    forced onto the inline ``with "..."`` fallback.
    """
    if get_client_mode() == "rich":
        return True
    return _client_supports_gmcp_package(context.player, "Editor")


def _client_supports_gmcp_package(obj, package: str) -> bool:
    """
    True when the player avatar ``obj``'s SSH session has advertised
    support for the named GMCP package via ``Core.Supports.Set`` /
    ``Core.Supports.Add``. Reads the same in-process / Django-cache
    fallback chain as :func:`_client_supports`.
    """
    from django.core.cache import cache  # pylint: disable=import-outside-toplevel

    from ..shell import prompt as prompt_module  # pylint: disable=import-outside-toplevel

    user_pk = _player_user_pk(obj)
    if user_pk is None:
        return False
    settings = prompt_module._session_settings.get(user_pk, {})  # pylint: disable=protected-access
    iac = settings.get("iac")
    if not iac:
        iac = cache.get(f"moo:session:{user_pk}:iac") or {}
    pkgs = iac.get("gmcp_packages") or {}
    return package in pkgs


def send_oob(obj, data: bytes):
    """
    Send a raw IAC subnegotiation frame to ``obj``'s SSH channel.

    Publishes an ``{"event": "oob", "data": <bytes>}`` Kombu message to the
    player's queue; the SSH server's ``_route_event`` writes the bytes
    directly onto the channel with no LF→CRLF translation.

    :param obj: the Object (player avatar) whose channel should receive the frame
    :param data: pre-encoded IAC subnegotiation bytes (``IAC SB ... IAC SE``)
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can send OOB data.")
    if not isinstance(data, (bytes, bytearray)):
        raise UserError(f"send_oob data must be bytes, not {type(data).__name__}.")
    _publish_to_player(obj, {"event": "oob", "data": bytes(data)})


def send_gmcp(obj, module: str, data=None):
    """
    Send a GMCP event to ``obj``'s SSH channel.

    GMCP (Generic MUD Communication Protocol) is the canonical OOB channel
    for structured MUD events. Clients that negotiated GMCP receive
    ``IAC SB GMCP <module> <json> IAC SE``; clients that did not see it as
    zero bytes on the wire (the SSH server skips the emit if the capability
    flag is false).

    Example::

        send_gmcp(player, "Char.Vitals", {"hp": 50, "maxhp": 100})
        send_gmcp(player, "Room.Info", {"num": 12, "name": "A dim hall"})
        send_gmcp(player, "Core.Ping")  # no payload

    :param obj: the Object (player avatar) to send the GMCP event to
    :param module: GMCP module/package name, e.g. ``"Char.Vitals"``
    :param data: JSON-serializable value, or ``None`` for an empty event
    """
    from ..shell.iac import encode_gmcp  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can send GMCP events.")
    if not _client_supports(obj, "gmcp"):
        return
    send_oob(obj, encode_gmcp(module, data))


def room_info_payload(room) -> dict:
    """
    Build the IRE-style GMCP ``Room.Info`` payload for ``room``.

    Returns ``{"num", "name", "exits"}`` with values stringified per the
    Achaea/Aardwolf/Mudlet-generic-mapper convention. Exit keys are
    normalized to short codes (``n``, ``ne``, ``u``, …); custom-named
    exits (``"ladder"``, ``"portal"``) round-trip unchanged so they still
    appear on the client.

    DjangoMOO names cardinal exits ``"<direction> from <room>"`` — e.g.
    ``"east from grand foyer"`` — to keep them globally unique. We check
    the exit's exact name, then its first word, then its aliases for a
    direction match before falling back to the raw name.

    :param room: an Object representing a room
    :returns: a dict suitable for ``send_gmcp(player, "Room.Info", payload)``
    """
    from . import DIRECTION_SHORTCODES  # pylint: disable=import-outside-toplevel

    exits_dict: dict[str, str] = {}
    for exit_obj in room.get_property_objects("exits") or []:
        if not exit_obj.dest:
            continue
        exit_name = (exit_obj.name or "").lower()
        key = DIRECTION_SHORTCODES.get(exit_name)
        if key is None and exit_name:
            first = exit_name.split()[0]
            key = DIRECTION_SHORTCODES.get(first)
        if key is None:
            try:
                for alias_obj in exit_obj.aliases.all():
                    alias = (alias_obj.alias or "").lower()
                    if alias in DIRECTION_SHORTCODES:
                        key = DIRECTION_SHORTCODES[alias]
                        break
            except AttributeError:
                pass
        if key is None:
            key = exit_name or exit_obj.name
        exits_dict[key] = str(exit_obj.dest.pk)
    return {"num": str(room.pk), "name": room.name, "exits": exits_dict}


def play_sound(obj, name: str, volume: int = 100, priority: int = 10):
    """
    Play a sound on ``obj``'s client.

    Prefers GMCP ``Client.Media.Play`` when the client negotiated GMCP;
    falls back to the inline MSP ``!!SOUND(...)`` marker if the client
    negotiated MSP; no-ops otherwise.

    DjangoMOO does not bundle any sound assets. Sound pack authors are
    expected to provide filenames that their client-side pack can
    resolve.

    :param obj: the player to play the sound on
    :param name: filename (client-resolvable), e.g. ``"door.wav"``
    :param volume: 0–100
    :param priority: higher numbers preempt lower-priority sounds
    """
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    from ..shell.iac import msp_sound_marker  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can play sounds.")
    if _client_supports(obj, "gmcp"):
        send_gmcp(obj, "Client.Media.Play", {"name": name, "volume": volume, "priority": priority})
        return
    if _client_supports(obj, "msp"):
        _publish_to_player(obj, msp_sound_marker(name, volume=volume, priority=priority))


def _client_supports(obj, capability: str) -> bool:
    """
    Check whether the player avatar ``obj``'s SSH session negotiated
    ``capability`` (``"gmcp"``, ``"mssp"``, ``"msp"``, ``"eor"``, ``"charset"``).

    Returns ``False`` for non-player objects and for players not currently
    connected. Reads from the in-process session-settings dict first, then
    falls back to the Django cache so Celery workers can make the same
    determination.
    """
    from django.core.cache import cache  # pylint: disable=import-outside-toplevel

    from ..shell import prompt as prompt_module  # pylint: disable=import-outside-toplevel

    user_pk = _player_user_pk(obj)
    if user_pk is None:
        return False
    settings = prompt_module._session_settings.get(user_pk, {})  # pylint: disable=protected-access
    iac = settings.get("iac")
    if not iac:
        iac = cache.get(f"moo:session:{user_pk}:iac") or {}
    return bool(iac.get(capability, False))


def boot_player(obj):
    """

    Disconnect the given player from the MOO server.

    Publishes a ``disconnect`` event to the player's Kombu message queue,
    which the SSH server's ``process_messages()`` loop picks up and exits cleanly.

    Permission: the caller must be the player being booted, or a wizard.

    :param obj: the player Object to disconnect
    """
    from moo.core import _publish_to_player

    caller = context.caller
    if caller and caller != obj and not caller.is_wizard():
        raise UserError("Only wizards can boot other players.")
    _publish_to_player(obj, {"event": "disconnect"})
