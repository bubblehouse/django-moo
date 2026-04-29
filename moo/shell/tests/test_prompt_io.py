# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for the prompt's outbound rendering and wire-format behaviour.

Covers _make_key_bindings, writer() in rich/raw modes, OSC 133 prompt
markers, generate_prompt(), the IAC prompt-end marker (EOR/GA/no-op),
and the "oob" route_event path.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from prompt_toolkit import ANSI
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings

import moo.shell.prompt as prompt_module
from moo.shell.prompt import MODE_RAW, MODE_RICH, MooPrompt, PROMPT_SHORTCUTS, _make_key_bindings


@pytest.fixture(autouse=True)
def _clean_session_settings():
    """Clear the module-level _session_settings dict before and after each test."""
    prompt_module._session_settings.clear()
    yield
    prompt_module._session_settings.clear()


def _make_prompt_user(name, location=None):
    """Build a mock user whose avatar has the given name and location."""
    avatar = MagicMock()
    avatar.name = name
    avatar.location = location
    user = MagicMock()
    user.player.avatar = avatar
    return user, avatar


# ---------------------------------------------------------------------------
# Key bindings
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
    expected_text = template.replace("%", "")
    expected_pos = template.find("%")
    event.app.current_buffer.set_document.assert_called_once_with(Document(expected_text, expected_pos))


def test_shortcut_handler_cursor_at_end_when_no_percent():
    """Shortcut handler places the cursor at the end of the text when the template contains no %."""
    original = prompt_module.PROMPT_SHORTCUTS.copy()
    prompt_module.PROMPT_SHORTCUTS = {"!": "emote"}
    try:
        kb = _make_key_bindings()
        binding = next(b for b in kb.bindings if b.keys[0] == "!")
        event = MagicMock()
        binding.handler(event)
        event.app.current_buffer.set_document.assert_called_once_with(Document("emote", 5))
    finally:
        prompt_module.PROMPT_SHORTCUTS = original


# ---------------------------------------------------------------------------
# generate_prompt
# ---------------------------------------------------------------------------


def test_generate_prompt_is_stable_marker():
    """The prompt is a single stable marker. Per-room state belongs in
    GMCP Room.Info so MUD-client mappers and screen readers can rely on
    a constant prompt pattern.
    """
    location = MagicMock()
    location.name = "The Laboratory"
    user, _ = _make_prompt_user("Wizard", location=location)
    result = asyncio.run(MooPrompt(user).generate_prompt())
    assert result == [("class:pound", ">>> ")]


def test_generate_prompt_no_location_still_stable():
    """The prompt does not change shape when the avatar has no location."""
    user, _ = _make_prompt_user("Wizard", location=None)
    result = asyncio.run(MooPrompt(user).generate_prompt())
    assert result == [("class:pound", ">>> ")]


# ---------------------------------------------------------------------------
# writer
# ---------------------------------------------------------------------------


def test_writer_rich_mode_uses_print_formatted_text():
    """writer() passes rendered ANSI output to print_formatted_text in rich mode."""
    prompt = MooPrompt(MagicMock())
    with patch("moo.shell.prompt.print_formatted_text") as mock_print:
        prompt.writer("hello [bold]world[/bold]")
    mock_print.assert_called_once()
    args, _ = mock_print.call_args
    assert isinstance(args[0], ANSI)


def test_writer_raw_mode_writes_to_chan():
    """writer() bypasses print_formatted_text and writes directly to the SSH channel in raw mode."""
    user = MagicMock()
    session = MagicMock()
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    with patch("moo.shell.prompt.print_formatted_text") as mock_print:
        prompt.writer("hello world")
    mock_print.assert_not_called()
    session._chan.write.assert_called_once()
    written = session._chan.write.call_args[0][0]
    assert "hello" in written
    assert written.endswith("\r\n")


def test_writer_raw_mode_rich_capture_preserves_colour():
    """writer() in raw mode writes SGR escape sequences to the channel for styled markup."""
    user = MagicMock()
    session = MagicMock()
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    prompt.writer("[red]alert[/red]")
    written = session._chan.write.call_args[0][0]
    assert "\x1b[" in written
    assert "alert" in written


# ---------------------------------------------------------------------------
# OSC 133 prompt markers
# ---------------------------------------------------------------------------


def test_osc133_disabled_for_iac_sessions():
    """
    MUD-client (IAC-enabled) sessions skip OSC 133 wrapping — Mudlet doesn't
    parse OSC 133 and the BEL-terminated frames swallow the trailing IAC GA,
    breaking the mapper's prompt-line detection.
    """
    user = MagicMock()
    user.pk = 4250
    session = MagicMock()
    session.iac_enabled = True
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    assert prompt._osc133_enabled() is False


def test_osc133_enabled_for_vanilla_ssh():
    """Vanilla SSH sessions retain OSC 133 wrapping (the default)."""
    user = MagicMock()
    user.pk = 4251
    session = MagicMock()
    session.iac_enabled = False
    prompt = MooPrompt(user, session=session, mode=MODE_RICH)
    assert prompt._osc133_enabled() is True


# ---------------------------------------------------------------------------
# IAC prompt-end marker
# ---------------------------------------------------------------------------


def test_prompt_end_marker_emits_eor_when_negotiated():
    """After a prompt render, IAC EOR goes to the channel when the client negotiated EOR."""
    from moo.shell.iac import EOR, IAC
    from moo.shell.prompt import _session_settings

    user = MagicMock()
    user.pk = 4242
    session = MagicMock()
    session.iac_enabled = True
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    _session_settings.setdefault(user.pk, {})["iac"] = {"eor": True}
    try:
        prompt._emit_prompt_end_marker()
    finally:
        _session_settings.pop(user.pk, None)
    session._chan.write.assert_called_once()
    written = session._chan.write.call_args[0][0]
    assert written.encode("utf-8", errors="surrogateescape") == bytes((IAC, EOR))


def test_prompt_end_marker_defaults_to_ga_for_iac_sessions():
    """
    When the session is IAC-enabled but EOR was not negotiated, the prompt-end
    marker defaults to IAC GA — the MUD convention; Mudlet's mapper relies on
    it for prompt boundary detection.
    """
    from moo.shell.iac import GA, IAC

    user = MagicMock()
    user.pk = 4243
    session = MagicMock()
    session.iac_enabled = True
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    prompt._emit_prompt_end_marker()
    session._chan.write.assert_called_once()
    written = session._chan.write.call_args[0][0]
    assert written.encode("utf-8", errors="surrogateescape") == bytes((IAC, GA))


def test_prompt_end_marker_noop_for_vanilla_ssh():
    """No IAC bytes are emitted when the session is not IAC-enabled."""
    user = MagicMock()
    user.pk = 4244
    session = MagicMock()
    session.iac_enabled = False
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    prompt._emit_prompt_end_marker()
    session._chan.write.assert_not_called()


# ---------------------------------------------------------------------------
# OOB route_event — raw IAC byte passthrough
# ---------------------------------------------------------------------------


def test_route_event_oob_writes_iac_bytes_via_surrogate_str():
    """
    The "oob" event hands raw IAC bytes to ``_chan_write_iac``, which converts
    them to surrogate-escaped str so the channel's UTF-8 encoder re-emits the
    original bytes on the wire.
    """
    from moo.shell.iac import IAC, OPT_GMCP, SB, SE

    user = MagicMock()
    session = MagicMock()
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    frame = bytes((IAC, SB, OPT_GMCP)) + b"Core.Hello" + bytes((IAC, SE))
    asyncio.run(prompt._route_event({"event": "oob", "data": frame}))
    session._chan.write.assert_called_once()
    written = session._chan.write.call_args[0][0]
    # Round-trip: surrogate-escape str re-encodes back to the original bytes.
    assert written.encode("utf-8", errors="surrogateescape") == frame
