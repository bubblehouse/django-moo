# -*- coding: utf-8 -*-

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from prompt_toolkit import ANSI
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings

import moo.shell.prompt as prompt_module
from moo.shell.prompt import MooPrompt, PROMPT_SHORTCUTS, _make_key_bindings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_make_key_bindings_returns_keybindings():
    """_make_key_bindings() returns a KeyBindings with one binding per PROMPT_SHORTCUT entry."""
    kb = _make_key_bindings()
    assert isinstance(kb, KeyBindings)
    registered_keys = {b.keys[0] for b in kb.bindings}
    for char in PROMPT_SHORTCUTS:
        assert char in registered_keys


def test_shortcut_handler_expands_with_cursor_at_percent():
    """Shortcut handler replaces the buffer with the template text and places the cursor at the % position."""
    kb = _make_key_bindings()
    binding = next(b for b in kb.bindings if b.keys[0] == '"')
    event = MagicMock()
    binding.handler(event)
    template = PROMPT_SHORTCUTS['"']
    expected_text = template.replace('%', '')
    expected_pos = template.find('%')
    event.app.current_buffer.set_document.assert_called_once_with(Document(expected_text, expected_pos))


def test_shortcut_handler_cursor_at_end_when_no_percent():
    """Shortcut handler places the cursor at the end of the text when the template contains no %."""
    original = prompt_module.PROMPT_SHORTCUTS.copy()
    prompt_module.PROMPT_SHORTCUTS = {'!': 'emote'}
    try:
        kb = _make_key_bindings()
        binding = next(b for b in kb.bindings if b.keys[0] == '!')
        event = MagicMock()
        binding.handler(event)
        event.app.current_buffer.set_document.assert_called_once_with(Document('emote', 5))
    finally:
        prompt_module.PROMPT_SHORTCUTS = original


def test_init():
    """MooPrompt initialises with correct default state and async queues."""
    user = MagicMock()
    prompt = MooPrompt(user)
    assert prompt.user is user
    assert prompt.is_exiting is False
    assert isinstance(prompt.editor_queue, asyncio.Queue)
    assert isinstance(prompt.paginator_queue, asyncio.Queue)
    assert prompt.last_property_write is None


def _make_prompt_user(name, location=None):
    """Build a mock user whose avatar has the given name and location."""
    avatar = MagicMock()
    avatar.name = name
    avatar.location = location
    user = MagicMock()
    user.player.avatar = avatar
    return user, avatar


def test_generate_prompt_with_location():
    """generate_prompt() includes the avatar's location name in the prompt."""
    location = MagicMock()
    location.name = "The Laboratory"
    user, _ = _make_prompt_user("Wizard", location=location)
    result = asyncio.run(MooPrompt(user).generate_prompt())
    assert len(result) == 5
    assert ("class:name", "Wizard") in result
    assert ("class:at", "@") in result
    assert ("class:location", "The Laboratory") in result
    assert ("class:colon", ":") in result
    assert ("class:pound", "$ ") in result


def test_generate_prompt_no_location():
    """generate_prompt() shows 'nowhere' when the avatar has no location."""
    user, _ = _make_prompt_user("Wizard", location=None)
    result = asyncio.run(MooPrompt(user).generate_prompt())
    assert ("class:location", "nowhere") in result


def test_writer_renders_markup():
    """writer() passes rendered ANSI output to print_formatted_text."""
    prompt = MooPrompt(MagicMock())
    with patch("moo.shell.prompt.print_formatted_text") as mock_print:
        prompt.writer("hello [bold]world[/bold]")
    mock_print.assert_called_once()
    args, _ = mock_print.call_args
    assert isinstance(args[0], ANSI)


def test_run_editor_session_invokes_callback():
    """run_editor_session() calls invoke_verb.delay when editor returns text and callback fields are set."""
    prompt = MooPrompt(MagicMock())
    req = {
        "content": "hello\nworld",
        "content_type": "text",
        "caller_id": 1,
        "player_id": 2,
        "callback_this_id": 3,
        "callback_verb_name": "edit_callback",
        "args": ["extra"],
    }
    wizard_caller = MagicMock()
    wizard_caller.is_wizard.return_value = True
    with patch("moo.shell.editor.run_editor", new=AsyncMock(return_value="edited text")):
        with patch("moo.shell.prompt.models.Object.objects.get", return_value=wizard_caller):
            with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
                asyncio.run(prompt.run_editor_session(req))
    mock_task.delay.assert_called_once_with(
        "edited text",
        "extra",
        caller_id=1,
        player_id=2,
        this_id=3,
        verb_name="edit_callback",
    )


def test_run_editor_session_rejects_non_wizard_caller_id():
    """run_editor_session() must not invoke the callback when caller_id is not a wizard (forged event guard)."""
    prompt = MooPrompt(MagicMock())
    req = {
        "content": "hello\nworld",
        "content_type": "text",
        "caller_id": 99,
        "player_id": 99,
        "callback_this_id": 3,
        "callback_verb_name": "edit_callback",
    }
    non_wizard_caller = MagicMock()
    non_wizard_caller.is_wizard.return_value = False
    with patch("moo.shell.editor.run_editor", new=AsyncMock(return_value="edited text")):
        with patch("moo.shell.prompt.models.Object.objects.get", return_value=non_wizard_caller):
            with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
                asyncio.run(prompt.run_editor_session(req))
    mock_task.delay.assert_not_called()


def test_run_editor_session_no_invoke_when_cancelled():
    """run_editor_session() does not call invoke_verb.delay when the user cancels (run_editor returns None)."""
    prompt = MooPrompt(MagicMock())
    req = {
        "content": "hello\nworld",
        "content_type": "text",
        "caller_id": 1,
        "player_id": 2,
        "callback_this_id": 3,
        "callback_verb_name": "edit_callback",
    }
    with patch("moo.shell.editor.run_editor", new=AsyncMock(return_value=None)):
        with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
            asyncio.run(prompt.run_editor_session(req))
    mock_task.delay.assert_not_called()


def test_run_editor_session_no_invoke_without_callback():
    """run_editor_session() does not call invoke_verb.delay when callback fields are absent."""
    prompt = MooPrompt(MagicMock())
    req = {
        "content": "hello\nworld",
        "content_type": "text",
        # no callback_this_id or callback_verb_name
    }
    with patch("moo.shell.editor.run_editor", new=AsyncMock(return_value="edited text")):
        with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
            asyncio.run(prompt.run_editor_session(req))
    mock_task.delay.assert_not_called()


def test_run_paginator_session():
    """run_paginator_session() delegates to run_paginator with content and content_type."""
    prompt = MooPrompt(MagicMock())
    req = {"content": "page text", "content_type": "python"}
    with patch("moo.shell.paginator.run_paginator", new=AsyncMock()) as mock_paginator:
        asyncio.run(prompt.run_paginator_session(req))
    mock_paginator.assert_called_once_with("page text", "python")


def _make_handle_command_mocks():
    """Return (prompt, avatar, parse_task_mock) with patched parse_command and ContextManager."""
    user, avatar = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)
    parse_result = MagicMock()
    parse_result.get.return_value = []
    return prompt, avatar, parse_result


def test_handle_command_writes_property_on_first_command():
    """handle_command() writes last_connected_time on the first command (last_property_write is None)."""
    prompt, avatar, parse_result = _make_handle_command_mocks()
    with patch("moo.shell.prompt.tasks.parse_command") as mock_task, \
         patch("moo.shell.prompt.code.ContextManager") as mock_ctx:
        mock_task.delay.return_value = parse_result
        mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        asyncio.run(prompt.handle_command("look"))
    avatar.set_property.assert_called_once()
    args = avatar.set_property.call_args[0]
    assert args[0] == "last_connected_time"
    assert isinstance(args[1], datetime)
    assert prompt.last_property_write is not None


def test_handle_command_throttles_property_writes():
    """handle_command() skips the property write when fewer than 15 seconds have elapsed."""
    prompt, avatar, parse_result = _make_handle_command_mocks()
    prompt.last_property_write = datetime.now(timezone.utc)
    with patch("moo.shell.prompt.tasks.parse_command") as mock_task, \
         patch("moo.shell.prompt.code.ContextManager") as mock_ctx:
        mock_task.delay.return_value = parse_result
        mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        asyncio.run(prompt.handle_command("look"))
    avatar.set_property.assert_not_called()


def test_handle_command_writes_after_15_seconds():
    """handle_command() writes last_connected_time again after more than 15 seconds have elapsed."""
    prompt, avatar, parse_result = _make_handle_command_mocks()
    prompt.last_property_write = datetime.now(timezone.utc) - timedelta(seconds=16)
    with patch("moo.shell.prompt.tasks.parse_command") as mock_task, \
         patch("moo.shell.prompt.code.ContextManager") as mock_ctx:
        mock_task.delay.return_value = parse_result
        mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        asyncio.run(prompt.handle_command("look"))
    avatar.set_property.assert_called_once()
    args = avatar.set_property.call_args[0]
    assert args[0] == "last_connected_time"
    assert isinstance(args[1], datetime)
