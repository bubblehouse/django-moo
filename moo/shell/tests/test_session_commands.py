# -*- coding: utf-8 -*-
"""
Tests for shell-layer session control features.

Covers:
- TERM=moo-automation detection in MooPromptToolkitSSHSession.session_started()
- Session setting registry updates via process_messages()
- Global output prefix/suffix wrapping in handle_command() and process_messages()
- .flush / _drain_messages()
"""
# pylint: disable=protected-access

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from moo.shell.prompt import MooPrompt, _session_settings
from moo.shell.server import MooPromptToolkitSSHSession


# ---------------------------------------------------------------------------
# Helpers (copied from test_prompt.py so this file is self-contained)
# ---------------------------------------------------------------------------


def _make_prompt_user(name, location=None):
    """Build a mock user whose avatar has the given name and location."""
    avatar = MagicMock()
    avatar.name = name
    avatar.location = location
    user = MagicMock()
    user.player.avatar = avatar
    return user, avatar


def _make_handle_command_mocks():
    """Return (prompt, avatar, parse_task_mock) with patched parse_command and ContextManager."""
    user, avatar = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)
    parse_result = MagicMock()
    parse_result.get.return_value = []
    return prompt, avatar, parse_result


def _run_process_messages(prompt, messages):
    """
    Run process_messages() against a list of message dicts, then stop.

    Each item in ``messages`` becomes ``content["message"]`` as seen by the
    dispatch logic. After all messages are delivered, the helper sets
    ``prompt.is_exiting = True`` so the loop exits cleanly.
    """
    MockEmpty = type("MockEmpty", (Exception,), {})
    msg_iter = iter(messages)

    def get_nowait():
        try:
            body_dict = next(msg_iter)
            mock_msg = MagicMock()
            mock_msg.body = json.dumps({"message": body_dict, "caller_id": None})
            return mock_msg
        except StopIteration as exc:
            prompt.is_exiting = True
            raise MockEmpty() from exc

    mock_sb = MagicMock()
    mock_sb.Empty = MockEmpty
    mock_sb.get_nowait.side_effect = get_nowait

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    with (
        patch("asyncio.sleep", new=AsyncMock()),
        patch("moo.shell.prompt.app.default_connection", return_value=mock_conn),
        patch("moo.shell.prompt.simple.SimpleBuffer", return_value=mock_sb),
        patch("moo.shell.prompt.moojson.loads", side_effect=json.loads),
    ):
        asyncio.run(prompt.process_messages())


def _run_drain_messages(prompt, messages):
    """
    Run _drain_messages() against a list of message dicts.

    Each item in ``messages`` becomes ``content["message"]``.
    Returns the list of strings returned by _drain_messages().
    """
    MockEmpty = type("MockEmpty", (Exception,), {})
    msg_iter = iter(messages)

    def get_nowait():
        try:
            body_dict = next(msg_iter)
            mock_msg = MagicMock()
            mock_msg.body = json.dumps({"message": body_dict, "caller_id": None})
            return mock_msg
        except StopIteration as exc:
            raise MockEmpty() from exc

    mock_sb = MagicMock()
    mock_sb.Empty = MockEmpty
    mock_sb.get_nowait.side_effect = get_nowait

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    with (
        patch("moo.shell.prompt.app.default_connection", return_value=mock_conn),
        patch("moo.shell.prompt.simple.SimpleBuffer", return_value=mock_sb),
        patch("moo.shell.prompt.moojson.loads", side_effect=json.loads),
    ):
        return asyncio.run(prompt._drain_messages())


# ---------------------------------------------------------------------------
# TERM=moo-automation detection (moved from test_server.py)
# ---------------------------------------------------------------------------


def test_session_started_non_automation():
    """Terminal type without 'moo-automation' leaves is_automation False and enable_cpr unchanged."""
    session = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    session.enable_cpr = True
    chan = MagicMock()
    chan.get_terminal_type.return_value = "xterm-256color"
    session._chan = chan

    with patch.object(MooPromptToolkitSSHSession.__bases__[0], "session_started", lambda self: None):
        session.session_started()

    assert session.is_automation is False
    assert session.enable_cpr is True


def test_session_started_automation():
    """Terminal type containing 'moo-automation' sets is_automation=True and enable_cpr=False."""
    session = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    session.enable_cpr = True
    chan = MagicMock()
    chan.get_terminal_type.return_value = "moo-automation"
    session._chan = chan

    with patch.object(MooPromptToolkitSSHSession.__bases__[0], "session_started", lambda self: None):
        session.session_started()

    assert session.is_automation is True
    assert session.enable_cpr is False


def test_session_started_no_channel():
    """session_started() with _chan=None sets is_automation=False and does not crash."""
    session = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    session.enable_cpr = True
    session._chan = None

    with patch.object(MooPromptToolkitSSHSession.__bases__[0], "session_started", lambda self: None):
        session.session_started()

    assert session.is_automation is False


# ---------------------------------------------------------------------------
# Session setting registry (moved from test_prompt.py)
# ---------------------------------------------------------------------------


def test_session_setting_message_updates_registry():
    """process_messages() stores a session_setting event in _session_settings."""
    user = MagicMock()
    user.pk = 99
    prompt = MooPrompt(user)
    _session_settings.pop(99, None)

    try:
        _run_process_messages(prompt, [{"event": "session_setting", "key": "quiet_mode", "value": True}])
        assert _session_settings.get(99, {}).get("quiet_mode") is True
    finally:
        _session_settings.pop(99, None)


# ---------------------------------------------------------------------------
# handle_command() — global prefix/suffix
# ---------------------------------------------------------------------------


def test_handle_command_emits_global_prefix_and_suffix():
    """handle_command() wraps output with output_global_prefix and output_global_suffix."""
    prompt, _, parse_result = _make_handle_command_mocks()
    parse_result.get.return_value = ["room output"]
    user_pk = prompt.user.pk
    _session_settings[user_pk] = {"output_global_prefix": ">>>", "output_global_suffix": "<<<"}

    try:
        with (
            patch("moo.shell.prompt.tasks.parse_command") as mock_task,
            patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
        ):
            mock_task.delay.return_value = parse_result
            mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            result = asyncio.run(prompt.handle_command("look"))
    finally:
        _session_settings.pop(user_pk, None)

    assert result[0] == ">>>"
    assert "room output" in result
    assert result[-1] == "<<<"


def test_handle_command_global_markers_are_outermost():
    """When PREFIX/SUFFIX and global markers are both set, global markers are outermost."""
    prompt, _, parse_result = _make_handle_command_mocks()
    parse_result.get.return_value = ["room output"]
    user_pk = prompt.user.pk
    _session_settings[user_pk] = {
        "output_global_prefix": "G_START",
        "output_global_suffix": "G_END",
        "output_prefix": "CMD_START",
        "output_suffix": "CMD_END",
    }

    try:
        with (
            patch("moo.shell.prompt.tasks.parse_command") as mock_task,
            patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
        ):
            mock_task.delay.return_value = parse_result
            mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            result = asyncio.run(prompt.handle_command("look"))
    finally:
        _session_settings.pop(user_pk, None)

    assert result.index("G_START") < result.index("CMD_START")
    assert result.index("CMD_END") < result.index("G_END")


# ---------------------------------------------------------------------------
# process_messages() — global prefix/suffix wrapping of async tells
# ---------------------------------------------------------------------------


def test_plain_message_wrapped_with_global_prefix_suffix():
    """process_messages() wraps a plain text message with output_global_prefix/suffix."""
    user = MagicMock()
    user.pk = 77
    prompt = MooPrompt(user)
    _session_settings[77] = {"output_global_prefix": ">>>", "output_global_suffix": "<<<"}

    written = []
    try:
        with patch("moo.shell.prompt.run_in_terminal", new=AsyncMock()) as mock_rit:

            async def capture_write(fn):
                await fn()

            mock_rit.side_effect = capture_write
            with patch.object(prompt, "writer", side_effect=written.append):
                _run_process_messages(prompt, ["hello from another player"])
    finally:
        _session_settings.pop(77, None)

    assert written == [">>>", "hello from another player", "<<<"]


# ---------------------------------------------------------------------------
# _drain_messages()
# ---------------------------------------------------------------------------


def test_drain_messages_writes_pending_text():
    """_drain_messages() returns each plain text message in the queue."""
    user = MagicMock()
    user.pk = 88
    prompt = MooPrompt(user)

    result = _run_drain_messages(prompt, ["msg one", "msg two"])

    assert result == ["msg one", "msg two"]


def test_drain_messages_processes_session_settings():
    """_drain_messages() applies session_setting events it encounters while draining."""
    user = MagicMock()
    user.pk = 89
    prompt = MooPrompt(user)
    _session_settings.pop(89, None)

    try:
        with patch.object(prompt, "writer", lambda _: None):
            _run_drain_messages(prompt, [{"event": "session_setting", "key": "quiet_mode", "value": True}])
        assert _session_settings.get(89, {}).get("quiet_mode") is True
    finally:
        _session_settings.pop(89, None)


def test_flush_command_calls_drain_messages():
    """process_commands() routes '.flush' to _drain_messages, not handle_command."""
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)

    drain_called = []
    handle_called = []

    async def fake_drain():
        drain_called.append(True)

    async def fake_handle(line):
        handle_called.append(line)

    prompt._drain_messages = fake_drain
    prompt.handle_command = fake_handle

    # Simulate one .flush input then EOF
    call_count = [0]

    async def fake_prompt(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return ".flush"
        raise EOFError()

    with (
        patch("moo.shell.prompt.PromptSession") as mock_ps,
        patch.object(prompt, "_fire_confunc", new=AsyncMock()),
        patch.object(prompt, "_fire_disfunc", new=AsyncMock()),
        patch.object(prompt, "generate_prompt", new=AsyncMock(return_value=[("", "$ ")])),
    ):
        mock_session = MagicMock()
        mock_session.prompt_async = fake_prompt
        mock_ps.return_value = mock_session
        asyncio.run(prompt.process_commands())

    assert drain_called
    assert not handle_called


def test_startup_does_not_open_second_message_buffer():
    """
    Regression: process_commands() must not call _drain_messages during session
    startup. A prior implementation drained once before the prompt loop started,
    which opened a second Kombu SimpleBuffer on the same queue that raced with
    the persistent consumer in process_messages. The two consumers split
    incoming messages round-robin — every other page to the session was
    silently discarded into the short-lived buffer.
    """
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)

    drain_calls = []

    async def fake_drain():
        drain_calls.append(True)
        return []

    prompt._drain_messages = fake_drain

    async def fake_prompt(*args, **kwargs):  # pylint: disable=unused-argument
        raise EOFError()

    with (
        patch("moo.shell.prompt.PromptSession") as mock_ps,
        patch.object(prompt, "_mark_connected", new=AsyncMock()),
        patch.object(prompt, "_fire_confunc", new=AsyncMock(return_value=[])),
        patch.object(prompt, "_await_tasks", new=AsyncMock()),
        patch.object(prompt, "_fire_disfunc", new=AsyncMock()),
        patch.object(prompt, "generate_prompt", new=AsyncMock(return_value=[("", "$ ")])),
    ):
        mock_session = MagicMock()
        mock_session.prompt_async = fake_prompt
        mock_ps.return_value = mock_session
        asyncio.run(prompt.process_commands())

    assert not drain_calls, "startup must not open a second SimpleBuffer via _drain_messages"
