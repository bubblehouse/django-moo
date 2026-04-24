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

    In automation mode (TERM=moo-automation), the SSH server intercepts the
    paginator event and writes the content directly to the terminal instead of
    opening the interactive UI.

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

    player = context.player
    if not player:
        return default

    user_pk = player.owner.pk if player.owner else None
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

    user_pk = player.owner.pk if player.owner else None
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
    suggest the inline ``@edit ... with "..."`` form instead.
    """
    return get_session_setting("mode", "rich")


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
