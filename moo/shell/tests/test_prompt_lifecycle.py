# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for the prompt's REPL lifecycle and inbound event dispatch.

Covers:
  - MooPrompt construction (queues, mode stamping, _chan plumbing)
  - process_commands() dispatch to rich/raw
  - _repl_setup / _repl_teardown lifecycle hooks
  - handle_command() property-write throttling and event-cache draining
  - process_messages() dispatch (paginator + plain tell, raw vs rich)
  - _fire_confunc / _await_tasks login hooks
  - disconnect-event handling
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import moo.shell.prompt as prompt_module
from moo.shell.prompt import MODE_RAW, MODE_RICH, MooPrompt


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


def _make_handle_command_mocks():
    """Return (prompt, avatar, parse_task_mock) with patched parse_command and ContextManager."""
    user, avatar = _make_prompt_user("Wizard")
    prompt = MooPrompt(user)
    parse_result = MagicMock()
    parse_result.get.return_value = ([], 0)
    parse_result.id = "test-task-id"
    return prompt, avatar, parse_result


def _make_avatar(has_confunc=True, has_location_confunc=True):
    """Return a mock avatar with optional confunc verbs on self and location."""
    location = MagicMock()
    location.has_verb.return_value = has_location_confunc

    avatar = MagicMock()
    avatar.has_verb.return_value = has_confunc
    avatar.location = location

    user = MagicMock()
    user.pk = 1
    user.player.avatar = avatar
    return user, avatar


def _run_process_messages(prompt, messages):
    """
    Run process_messages() against a list of message dicts, then stop.

    Each item in ``messages`` becomes ``content["message"]`` as seen by the
    dispatch logic. After all messages are delivered, ``is_exiting`` is set
    so the loop terminates.
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
    prompt._session_buffer = mock_sb
    prompt.startup_drain_complete.set()
    prompt.prompt_app_ready.set()
    # The real _chan is a live SSH channel; MagicMock's auto-generated
    # is_closing() returns truthy and would short-circuit the loop.
    prompt._chan = None

    with (
        patch("asyncio.sleep", new=AsyncMock()),
        patch("moo.shell.prompt.moojson.loads", side_effect=json.loads),
    ):
        asyncio.run(prompt.process_messages())


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_init():
    """MooPrompt initialises with correct default state and async queues."""
    user = MagicMock()
    prompt = MooPrompt(user)
    assert prompt.user is user
    assert prompt.is_exiting is False
    assert isinstance(prompt.editor_queue, asyncio.Queue)
    assert isinstance(prompt.paginator_queue, asyncio.Queue)
    assert isinstance(prompt.disconnect_event, asyncio.Event)
    assert not prompt.disconnect_event.is_set()
    assert prompt.last_property_write is None
    assert prompt.mode == MODE_RICH
    assert prompt_module._session_settings[user.pk]["mode"] == MODE_RICH


def test_init_raw_mode_stamps_session_settings():
    """Passing mode=MODE_RAW records the mode in session settings and stores the channel."""
    user = MagicMock()
    session = MagicMock()
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    assert prompt.mode == MODE_RAW
    assert prompt_module._session_settings[user.pk]["mode"] == MODE_RAW
    assert prompt._chan is session._chan


# ---------------------------------------------------------------------------
# process_commands dispatch
# ---------------------------------------------------------------------------


def test_process_commands_dispatches_to_rich():
    """process_commands() routes to process_commands_rich when mode is rich."""
    user = MagicMock()
    prompt = MooPrompt(user, mode=MODE_RICH)
    with (
        patch.object(MooPrompt, "process_commands_rich", new=AsyncMock()) as rich,
        patch.object(MooPrompt, "process_commands_raw", new=AsyncMock()) as raw,
    ):
        asyncio.run(prompt.process_commands())
    rich.assert_awaited_once()
    raw.assert_not_awaited()


def test_process_commands_dispatches_to_raw():
    """process_commands() routes to process_commands_raw when mode is raw."""
    user = MagicMock()
    prompt = MooPrompt(user, session=MagicMock(), mode=MODE_RAW)
    with (
        patch.object(MooPrompt, "process_commands_rich", new=AsyncMock()) as rich,
        patch.object(MooPrompt, "process_commands_raw", new=AsyncMock()) as raw,
    ):
        asyncio.run(prompt.process_commands())
    raw.assert_awaited_once()
    rich.assert_not_awaited()


# ---------------------------------------------------------------------------
# handle_command — property-write throttling + cache events
# ---------------------------------------------------------------------------


def test_handle_command_writes_property_on_first_command():
    """handle_command() writes last_connected_time on the first command (last_property_write is None)."""
    prompt, avatar, parse_result = _make_handle_command_mocks()
    with (
        patch("moo.shell.prompt.tasks.parse_command") as mock_task,
        patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
    ):
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
    with (
        patch("moo.shell.prompt.tasks.parse_command") as mock_task,
        patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
    ):
        mock_task.delay.return_value = parse_result
        mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        asyncio.run(prompt.handle_command("look"))
    avatar.set_property.assert_not_called()


def test_handle_command_writes_after_15_seconds():
    """handle_command() writes last_connected_time again after more than 15 seconds have elapsed."""
    prompt, avatar, parse_result = _make_handle_command_mocks()
    prompt.last_property_write = datetime.now(timezone.utc) - timedelta(seconds=16)
    with (
        patch("moo.shell.prompt.tasks.parse_command") as mock_task,
        patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
    ):
        mock_task.delay.return_value = parse_result
        mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        asyncio.run(prompt.handle_command("look"))
    avatar.set_property.assert_called_once()
    args = avatar.set_property.call_args[0]
    assert args[0] == "last_connected_time"
    assert isinstance(args[1], datetime)


def test_handle_command_reads_events_from_cache():
    """handle_command() returns the event list stashed in the cache under the task id and clears the key."""
    prompt, _, parse_result = _make_handle_command_mocks()
    parse_result.id = "task-xyz"

    def _fake_cache_get(key):
        if key == "moo:task_events:task-xyz":
            return ["input_prompt"]
        return None

    delete_calls = []
    with (
        patch("moo.shell.prompt.tasks.parse_command") as mock_task,
        patch("moo.shell.prompt.code.ContextManager") as mock_ctx,
        patch("django.core.cache.cache.get", side_effect=_fake_cache_get),
        patch("django.core.cache.cache.delete", side_effect=delete_calls.append),
    ):
        mock_task.delay.return_value = parse_result
        mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        _to_write, events = asyncio.run(prompt.handle_command("look"))
    assert events == ["input_prompt"]
    assert "moo:task_events:task-xyz" in delete_calls


# ---------------------------------------------------------------------------
# _fire_confunc / _await_tasks
# ---------------------------------------------------------------------------


def test_fire_confunc_returns_task_results():
    """_fire_confunc() returns one AsyncResult per dispatched task."""
    user, _ = _make_avatar(has_confunc=True, has_location_confunc=True)
    prompt = MooPrompt(user)
    task_result = MagicMock()
    with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
        mock_task.delay.return_value = task_result
        results = asyncio.run(prompt._fire_confunc())
    assert results == [task_result, task_result]
    assert mock_task.delay.call_count == 2


def test_fire_confunc_skips_missing_verbs():
    """_fire_confunc() returns an empty list when the player has no confunc verbs."""
    user, _ = _make_avatar(has_confunc=False, has_location_confunc=False)
    prompt = MooPrompt(user)
    with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
        results = asyncio.run(prompt._fire_confunc())
    assert results == []
    mock_task.delay.assert_not_called()


def test_await_tasks_waits_for_each_result():
    """_await_tasks() calls .get() on every task result."""
    user = MagicMock()
    prompt = MooPrompt(user)
    r1, r2 = MagicMock(), MagicMock()
    asyncio.run(prompt._await_tasks([r1, r2]))
    r1.get.assert_called_once_with(timeout=10, propagate=False)
    r2.get.assert_called_once_with(timeout=10, propagate=False)


def test_await_tasks_swallows_task_failure():
    """_await_tasks() does not propagate exceptions so a broken confunc verb cannot block login."""
    user = MagicMock()
    prompt = MooPrompt(user)
    bad_result = MagicMock()
    bad_result.get.side_effect = Exception("confunc exploded")
    asyncio.run(prompt._await_tasks([bad_result]))  # must not raise


# ---------------------------------------------------------------------------
# process_messages event dispatch
# ---------------------------------------------------------------------------


def test_disconnect_message_sets_is_exiting():
    """process_messages() sets is_exiting and fires disconnect_event on a disconnect event."""
    user = MagicMock()
    user.pk = 42
    prompt = MooPrompt(user)

    _run_process_messages(prompt, [{"event": "disconnect"}])

    assert prompt.is_exiting is True
    assert prompt.disconnect_event.is_set()


def test_process_messages_raw_mode_paginator_dumps_inline():
    """Paginator events are dumped through writer() without paging in raw mode."""
    user = MagicMock()
    user.pk = 77
    prompt = MooPrompt(user, session=MagicMock(), mode=MODE_RAW)
    with patch.object(prompt, "writer") as mock_writer:
        _run_process_messages(prompt, [{"event": "paginator", "content": "lots of text"}])
    mock_writer.assert_any_call("lots of text")
    assert prompt.paginator_queue.empty()


def test_process_messages_raw_mode_plain_tell_skips_run_in_terminal():
    """Plain-message events reach writer() directly without run_in_terminal in raw mode."""
    user = MagicMock()
    user.pk = 78
    prompt = MooPrompt(user, session=MagicMock(), mode=MODE_RAW)
    with (
        patch.object(prompt, "writer") as mock_writer,
        patch("moo.shell.prompt.run_in_terminal", new=AsyncMock()) as mock_rit,
    ):
        _run_process_messages(prompt, ["hello from another player"])
    mock_rit.assert_not_awaited()
    mock_writer.assert_any_call("hello from another player")


def test_process_messages_rich_mode_plain_tell_uses_run_in_terminal():
    """Plain-message events go through run_in_terminal in rich mode."""
    user = MagicMock()
    user.pk = 79
    prompt = MooPrompt(user)  # rich by default
    with patch("moo.shell.prompt.run_in_terminal", new=AsyncMock()) as mock_rit:
        _run_process_messages(prompt, ["hello"])
    mock_rit.assert_awaited()


# ---------------------------------------------------------------------------
# _repl_setup / _repl_teardown
# ---------------------------------------------------------------------------


def test_repl_setup_teardown_roundtrip():
    """_repl_setup() stamps mode and _repl_teardown() clears it, with connect/disconnect fired."""
    user = MagicMock()
    user.pk = 91
    prompt = MooPrompt(user, mode=MODE_RICH)
    # _repl_setup writes 'mode' after clearing; teardown wipes the whole entry.
    prompt._mark_connected = AsyncMock()
    prompt._fire_confunc = AsyncMock(return_value=[])
    prompt._await_tasks = AsyncMock()
    prompt._fire_disfunc = AsyncMock()
    prompt._mark_disconnected = AsyncMock()
    with patch("django.core.cache.cache.set"), patch("django.core.cache.cache.delete"):
        asyncio.run(prompt._repl_setup())
        assert prompt_module._session_settings[user.pk]["mode"] == MODE_RICH
        prompt._mark_connected.assert_awaited_once()
        prompt._fire_confunc.assert_awaited_once()
        asyncio.run(prompt._repl_teardown())
    prompt._fire_disfunc.assert_awaited_once()
    prompt._mark_disconnected.assert_awaited_once()
    assert user.pk not in prompt_module._session_settings


# ---------------------------------------------------------------------------
# pre_run flushes pending connect output (Bug 1: initial look on connect)
# ---------------------------------------------------------------------------


def _make_pre_run_session():
    """Build a mock prompt_session whose output recorder captures write_raw calls."""
    written: list[str] = []
    output = MagicMock()
    output.write_raw.side_effect = written.append
    app = MagicMock()
    app.output = output
    session = MagicMock()
    session.app = app
    return session, written


def test_pre_run_flushes_pending_connect_output_with_osc133():
    """The pre_run callback flushes _pending_connect_output before the prompt
    renders, so the on-connect look is visible to the user."""
    user = MagicMock()
    user.pk = 100
    prompt = MooPrompt(user)
    prompt._pending_connect_output = "WELCOME TO THE ROOM\n"
    session, written = _make_pre_run_session()
    pre_run = prompt._make_pre_run(session, with_osc133=True)
    pre_run()
    assert "WELCOME TO THE ROOM\n" in written
    assert prompt._pending_connect_output == ""
    assert prompt.prompt_app_ready.is_set()


def test_pre_run_flushes_pending_connect_output_without_osc133():
    """Without OSC 133 (e.g. classic MUD clients via IAC), the pending
    connect output must STILL be flushed — otherwise the room description
    is silently dropped and the user sees a bare prompt."""
    user = MagicMock()
    user.pk = 101
    prompt = MooPrompt(user)
    prompt._pending_connect_output = "ROOM DESCRIPTION\n"
    session, written = _make_pre_run_session()
    pre_run = prompt._make_pre_run(session, with_osc133=False)
    pre_run()
    assert "ROOM DESCRIPTION\n" in written
    assert prompt._pending_connect_output == ""
    # Without osc133, render hooks must not be wired up.
    session.app.before_render.__iadd__.assert_not_called()
    session.app.after_render.__iadd__.assert_not_called()


def test_pre_run_no_pending_output_is_noop():
    """When there's nothing buffered, pre_run does not write to the output."""
    user = MagicMock()
    user.pk = 102
    prompt = MooPrompt(user)
    prompt._pending_connect_output = ""
    session, written = _make_pre_run_session()
    pre_run = prompt._make_pre_run(session, with_osc133=False)
    pre_run()
    assert not written
    assert prompt.prompt_app_ready.is_set()
