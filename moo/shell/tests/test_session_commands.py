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

from moo.shell.osc import OSC_133_OUTPUT_START, osc_133_command_end
from moo.shell.prompt import MooPrompt, _RawAnsi, _session_settings
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
    parse_result.get.return_value = ([], 0)
    parse_result.id = "test-task-id"
    return prompt, avatar, parse_result


def _install_mock_session_buffer(prompt, messages):
    """
    Attach a MagicMock ``SimpleBuffer`` to ``prompt`` that yields ``messages``.

    Each item becomes ``content["message"]`` as seen by the dispatch logic;
    once the iterator is exhausted, ``sb.Empty`` is raised to end the drain.
    Returns the mock so tests can assert on it if needed.
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
    prompt._session_buffer = mock_sb
    return mock_sb


def _run_process_messages(prompt, messages):
    """
    Run process_messages() against a list of message dicts, then stop.

    Each item in ``messages`` becomes ``content["message"]`` as seen by the
    dispatch logic. After all messages are delivered, the helper sets
    ``prompt.is_exiting = True`` so the loop exits cleanly.
    """
    _install_mock_session_buffer(prompt, messages)
    prompt.startup_drain_complete.set()
    prompt.prompt_app_ready.set()
    prompt._chan = None  # avoid MagicMock.is_closing() short-circuit

    # Stop the loop as soon as the last message is drained.
    real_drain = prompt._drain_session_buffer

    async def stopping_drain():
        result = await real_drain()
        if not result[0] and not result[1]:
            prompt.is_exiting = True
        return result

    prompt._drain_session_buffer = stopping_drain

    with (
        patch("asyncio.sleep", new=AsyncMock()),
        patch("moo.shell.prompt.moojson.loads", side_effect=json.loads),
    ):
        asyncio.run(prompt.process_messages())


def _run_drain_messages(prompt, messages):
    """
    Run _drain_messages() against a list of message dicts.

    Each item in ``messages`` becomes ``content["message"]``.
    Returns the list of strings returned by _drain_messages().
    """
    _install_mock_session_buffer(prompt, messages)

    with patch("moo.shell.prompt.moojson.loads", side_effect=json.loads):
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
    parse_result.get.return_value = (["room output"], 0)
    user_pk = prompt.user.pk
    _session_settings[user_pk] = {
        "output_global_prefix": ">>>",
        "output_global_suffix": "<<<",
        "osc133_mode": False,
    }

    try:
        with (
            patch("moo.shell.prompt.tasks.parse_command") as mock_task,
            patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
        ):
            mock_task.delay.return_value = parse_result
            mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            result, _events = asyncio.run(prompt.handle_command("look"))
    finally:
        _session_settings.pop(user_pk, None)

    assert result[0] == ">>>"
    assert "room output" in result
    assert result[-1] == "<<<"


def test_handle_command_global_markers_are_outermost():
    """When PREFIX/SUFFIX and global markers are both set, global markers are outermost."""
    prompt, _, parse_result = _make_handle_command_mocks()
    parse_result.get.return_value = (["room output"], 0)
    user_pk = prompt.user.pk
    _session_settings[user_pk] = {
        "output_global_prefix": "G_START",
        "output_global_suffix": "G_END",
        "output_prefix": "CMD_START",
        "output_suffix": "CMD_END",
        "osc133_mode": False,
    }

    try:
        with (
            patch("moo.shell.prompt.tasks.parse_command") as mock_task,
            patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
        ):
            mock_task.delay.return_value = parse_result
            mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            result, _events = asyncio.run(prompt.handle_command("look"))
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

    printed = []
    try:
        with (
            patch("moo.shell.prompt.run_in_terminal", new=AsyncMock()) as mock_rit,
            patch("moo.shell.prompt.print_formatted_text", side_effect=lambda content, **_: printed.append(content)),
        ):

            async def capture_write(fn):
                result = fn()
                if asyncio.iscoroutine(result):
                    await result

            mock_rit.side_effect = capture_write
            _run_process_messages(prompt, ["hello from another player"])
    finally:
        _session_settings.pop(77, None)

    # Rich mode concatenates prefix + message + suffix into a single rendered
    # ANSI blob and emits it via one print_formatted_text call, so the per-
    # piece call count is 1, not 3. Check the rendered content instead.
    assert len(printed) == 1
    rendered = printed[0].value if hasattr(printed[0], "value") else str(printed[0])
    assert ">>>" in rendered
    assert "hello from another player" in rendered
    assert "<<<" in rendered


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


def test_startup_opens_session_buffer_before_firing_confunc():
    """
    Regression: ``_repl_setup`` must open the player's Kombu consumer BEFORE
    dispatching confunc tasks, otherwise the room's ``tell()`` messages are
    published to the exchange while no queue exists (queues bind with
    ``auto_delete=True``) and get silently dropped. Connect-time ``look_self``
    output would intermittently vanish until the user issued a command that
    happened to land AFTER ``process_messages`` finally opened the consumer.
    """
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)

    order = []

    async def fake_open():
        order.append("open")

    async def fake_fire():
        order.append("fire")
        return []

    async def fake_drain():
        return [], []

    async def fake_prompt(*args, **kwargs):  # pylint: disable=unused-argument
        raise EOFError()

    with (
        patch("moo.shell.prompt.PromptSession") as mock_ps,
        patch.object(prompt, "_mark_connected", new=AsyncMock()),
        patch.object(prompt, "_open_session_buffer", new=fake_open),
        patch.object(prompt, "_close_session_buffer", new=AsyncMock()),
        patch.object(prompt, "_fire_confunc", new=fake_fire),
        patch.object(prompt, "_await_tasks", new=AsyncMock()),
        patch.object(prompt, "_drain_session_buffer", new=fake_drain),
        patch.object(prompt, "_fire_disfunc", new=AsyncMock()),
        patch.object(prompt, "generate_prompt", new=AsyncMock(return_value=[("", "$ ")])),
    ):
        mock_session = MagicMock()
        mock_session.prompt_async = fake_prompt
        mock_ps.return_value = mock_session
        asyncio.run(prompt.process_commands())

    assert order == ["open", "fire"], f"expected open before fire, got {order}"


# ---------------------------------------------------------------------------
# OSC 133 / accessibility prefix wrapping
# ---------------------------------------------------------------------------


def _run_handle_command(prompt, parse_result, line="look"):
    with (
        patch("moo.shell.prompt.tasks.parse_command") as mock_task,
        patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
    ):
        mock_task.delay.return_value = parse_result
        mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        return asyncio.run(prompt.handle_command(line))


def test_handle_command_wraps_with_osc133_by_default():
    """handle_command() prepends OSC 133;C and appends ;D;0 when osc133 is on (default)."""
    prompt, _, parse_result = _make_handle_command_mocks()
    parse_result.get.return_value = (["room output"], 0)
    user_pk = prompt.user.pk
    _session_settings.pop(user_pk, None)
    try:
        result, _events = _run_handle_command(prompt, parse_result)
    finally:
        _session_settings.pop(user_pk, None)

    assert isinstance(result[0], _RawAnsi)
    assert result[0] == OSC_133_OUTPUT_START
    assert isinstance(result[-1], _RawAnsi)
    assert result[-1] == osc_133_command_end(0)


def test_handle_command_wraps_with_exit_status_one_on_error():
    """handle_command() emits OSC 133;D;1 when parse_command reports exit_status=1."""
    prompt, _, parse_result = _make_handle_command_mocks()
    parse_result.get.return_value = (["[bold red]oops[/bold red]"], 1)
    user_pk = prompt.user.pk
    _session_settings.pop(user_pk, None)
    try:
        result, _events = _run_handle_command(prompt, parse_result)
    finally:
        _session_settings.pop(user_pk, None)

    assert result[-1] == osc_133_command_end(1)


def test_handle_command_skips_osc133_when_disabled():
    """handle_command() omits OSC 133 wrappers when osc133_mode is False."""
    prompt, _, parse_result = _make_handle_command_mocks()
    parse_result.get.return_value = (["room output"], 0)
    user_pk = prompt.user.pk
    _session_settings[user_pk] = {"osc133_mode": False}
    try:
        result, _events = _run_handle_command(prompt, parse_result)
    finally:
        _session_settings.pop(user_pk, None)

    assert not any(isinstance(p, _RawAnsi) for p in result)
    assert "room output" in result


def test_editor_rejection_includes_error_prefix_when_prefixes_on():
    """_editor_rejection_pieces wraps the message with [ERROR] when prefixes_mode is True."""
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)
    user_pk = prompt.user.pk
    _session_settings[user_pk] = {"prefixes_mode": True}
    try:
        pieces = prompt._editor_rejection_pieces()
    finally:
        _session_settings.pop(user_pk, None)

    assert any("[ERROR]" in p for p in pieces)


def test_editor_rejection_omits_error_prefix_when_prefixes_off():
    """_editor_rejection_pieces does NOT add [ERROR] when prefixes_mode is False (default)."""
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)
    user_pk = prompt.user.pk
    _session_settings.pop(user_pk, None)
    try:
        pieces = prompt._editor_rejection_pieces()
    finally:
        _session_settings.pop(user_pk, None)

    assert not any("[ERROR]" in p for p in pieces)


def test_osc133_default_on():
    """The osc133 accessor defaults to True when no setting is recorded."""
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)
    user_pk = prompt.user.pk
    _session_settings.pop(user_pk, None)
    try:
        assert prompt._osc133_enabled() is True
    finally:
        _session_settings.pop(user_pk, None)


def test_osc133_disabled_when_set_false():
    """The osc133 accessor honours an explicit False setting."""
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)
    user_pk = prompt.user.pk
    _session_settings[user_pk] = {"osc133_mode": False}
    try:
        assert prompt._osc133_enabled() is False
    finally:
        _session_settings.pop(user_pk, None)


def test_writer_emits_raw_ansi_to_chan_in_raw_mode():
    """writer() with a _RawAnsi argument writes the raw bytes to the channel without LF translation."""
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user, mode="raw")
    written = []
    prompt._chan = MagicMock()
    prompt._chan.write = written.append
    user_pk = prompt.user.pk
    _session_settings.setdefault(user_pk, {})["mode"] = "raw"
    try:
        prompt.writer(_RawAnsi(OSC_133_OUTPUT_START))
    finally:
        _session_settings.pop(user_pk, None)

    assert written == [OSC_133_OUTPUT_START]


def test_repl_setup_signals_startup_drain_complete():
    """_repl_setup must open the session buffer, fire confunc, and signal
    process_messages that startup has finished.

    The drain is deliberately deferred to ``process_messages`` so it runs
    via ``run_in_terminal`` after the prompt Application is live —
    draining directly to the SSH channel from ``_repl_setup`` would be
    wiped by the Application's initial erase-in-display.
    """
    user, _ = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)

    with (
        patch.object(prompt, "_mark_connected", new=AsyncMock()),
        patch.object(prompt, "_open_session_buffer", new=AsyncMock()) as mock_open,
        patch.object(prompt, "_fire_confunc", new=AsyncMock(return_value=[])) as mock_fire,
        patch.object(prompt, "_await_tasks", new=AsyncMock()) as mock_await,
        patch("django.core.cache.cache.set"),
    ):
        asyncio.run(prompt._repl_setup())

    mock_open.assert_awaited_once()
    mock_fire.assert_awaited_once()
    mock_await.assert_awaited_once()
    assert prompt.startup_drain_complete.is_set()
