# -*- coding: utf-8 -*-
# pylint: disable=protected-access

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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


def _make_prompt_user(name, location=None):
    """Build a mock user whose avatar has the given name and location."""
    avatar = MagicMock()
    avatar.name = name
    avatar.location = location
    user = MagicMock()
    user.player.avatar = avatar
    return user, avatar


def test_generate_prompt_is_stable_marker():
    """
    generate_prompt() returns a single stable ``>>> `` marker. Per-room
    state belongs in GMCP Room.Info so MUD-client mappers and screen
    readers can rely on a constant prompt pattern.
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


def test_prompt_end_marker_noop_for_vanilla_ssh():
    """No IAC bytes are emitted when the session is not IAC-enabled."""
    user = MagicMock()
    user.pk = 4244
    session = MagicMock()
    session.iac_enabled = False
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    prompt._emit_prompt_end_marker()
    session._chan.write.assert_not_called()


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
    parse_result.get.return_value = ([], 0)
    parse_result.id = "test-task-id"
    return prompt, avatar, parse_result


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


# ---------------------------------------------------------------------------
# process_messages() dispatch tests
# ---------------------------------------------------------------------------


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
# _fire_confunc() / _await_tasks() tests
# ---------------------------------------------------------------------------


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


def test_fire_confunc_returns_task_results():
    """_fire_confunc() returns one AsyncResult per dispatched task."""
    user, _ = _make_avatar(has_confunc=True, has_location_confunc=True)
    prompt = MooPrompt(user)
    task_result = MagicMock()
    with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
        mock_task.delay.return_value = task_result
        results = asyncio.run(prompt._fire_confunc())  # pylint: disable=protected-access
    assert results == [task_result, task_result]
    assert mock_task.delay.call_count == 2


def test_fire_confunc_skips_missing_verbs():
    """_fire_confunc() returns an empty list when the player has no confunc verbs."""
    user, _ = _make_avatar(has_confunc=False, has_location_confunc=False)
    prompt = MooPrompt(user)
    with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
        results = asyncio.run(prompt._fire_confunc())  # pylint: disable=protected-access
    assert results == []
    mock_task.delay.assert_not_called()


def test_await_tasks_waits_for_each_result():
    """_await_tasks() calls .get() on every task result."""
    user = MagicMock()
    prompt = MooPrompt(user)
    r1, r2 = MagicMock(), MagicMock()
    asyncio.run(prompt._await_tasks([r1, r2]))  # pylint: disable=protected-access
    r1.get.assert_called_once_with(timeout=10, propagate=False)
    r2.get.assert_called_once_with(timeout=10, propagate=False)


def test_await_tasks_swallows_task_failure():
    """_await_tasks() does not propagate exceptions so a broken confunc verb cannot block login."""
    user = MagicMock()
    prompt = MooPrompt(user)
    bad_result = MagicMock()
    bad_result.get.side_effect = Exception("confunc exploded")
    asyncio.run(prompt._await_tasks([bad_result]))  # pylint: disable=protected-access  # must not raise


def test_disconnect_message_sets_is_exiting():
    """process_messages() sets is_exiting and fires disconnect_event on a disconnect event."""
    user = MagicMock()
    user.pk = 42
    prompt = MooPrompt(user)

    _run_process_messages(prompt, [{"event": "disconnect"}])

    assert prompt.is_exiting is True
    assert prompt.disconnect_event.is_set()


# ---------------------------------------------------------------------------
# Prompt-flash fix: handle_command reads events from cache; run_input_session
# absorbs the callback chain in a single session.
# ---------------------------------------------------------------------------


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


def test_run_input_session_consumes_chain_without_prompt():
    """run_input_session() drains sequential input_prompt events from input_queue in a single call."""
    user = MagicMock()
    user.pk = 1
    prompt = MooPrompt(user)

    req1 = {
        "prompt": "Old password: ",
        "password": True,
        "caller_id": 1,
        "player_id": 1,
        "callback_this_id": 10,
        "callback_verb_name": "at_password_new",
        "args": [],
    }
    req2 = {
        "prompt": "New password: ",
        "password": True,
        "caller_id": 1,
        "player_id": 1,
        "callback_this_id": 10,
        "callback_verb_name": "at_password_confirm",
        "args": ["old-input"],
    }
    req3 = {
        "prompt": "Confirm: ",
        "password": True,
        "caller_id": 1,
        "player_id": 1,
        "callback_this_id": 10,
        "callback_verb_name": "at_password_commit",
        "args": ["old-input", "new-input"],
    }

    async def _run():
        await prompt.input_queue.put(req2)
        await prompt.input_queue.put(req3)
        answers = iter(["old-input", "new-input", "confirm-input"])

        class _MockSession:
            def __init__(self, *a, **kw):
                pass

            async def prompt_async(self, *a, **kw):  # pylint: disable=unused-argument
                return next(answers)

        wizard_caller = MagicMock()
        wizard_caller.is_wizard.return_value = True
        with (
            patch("moo.shell.prompt.PromptSession", _MockSession),
            patch("moo.shell.prompt.models.Object.objects.get", return_value=wizard_caller),
            patch("moo.shell.prompt.tasks.invoke_verb") as mock_task,
        ):
            await prompt.run_input_session(req1)
            return mock_task.delay.call_count

    invoke_count = asyncio.run(_run())
    # All three prompts handled inside one session (one delay per stage).
    assert invoke_count == 3
    # Queue fully drained — no lingering messages to race with the next prompt_async.
    assert prompt.input_queue.empty()


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


def test_raw_editor_event_emits_rejection_text():
    """An editor request in raw mode is refused with the inline-form hint."""
    user = MagicMock()
    prompt = MooPrompt(user, session=MagicMock(), mode=MODE_RAW)
    pieces = prompt._editor_rejection_pieces()  # pylint: disable=protected-access
    assert any("@edit" in p and "with" in p for p in pieces)


def test_repl_setup_teardown_roundtrip():
    """_repl_setup() stamps mode and _repl_teardown() clears it, with connect/disconnect fired."""
    user = MagicMock()
    user.pk = 91
    prompt = MooPrompt(user, mode=MODE_RICH)
    # _repl_setup writes 'mode' after clearing; teardown wipes the whole entry.
    prompt._mark_connected = AsyncMock()  # pylint: disable=protected-access
    prompt._fire_confunc = AsyncMock(return_value=[])  # pylint: disable=protected-access
    prompt._await_tasks = AsyncMock()  # pylint: disable=protected-access
    prompt._fire_disfunc = AsyncMock()  # pylint: disable=protected-access
    prompt._mark_disconnected = AsyncMock()  # pylint: disable=protected-access
    with patch("django.core.cache.cache.set"), patch("django.core.cache.cache.delete"):
        asyncio.run(prompt._repl_setup())  # pylint: disable=protected-access
        assert prompt_module._session_settings[user.pk]["mode"] == MODE_RICH
        prompt._mark_connected.assert_awaited_once()  # pylint: disable=protected-access
        prompt._fire_confunc.assert_awaited_once()  # pylint: disable=protected-access
        asyncio.run(prompt._repl_teardown())  # pylint: disable=protected-access
    prompt._fire_disfunc.assert_awaited_once()  # pylint: disable=protected-access
    prompt._mark_disconnected.assert_awaited_once()  # pylint: disable=protected-access
    assert user.pk not in prompt_module._session_settings


def test_run_input_session_exits_when_queue_times_out():
    """run_input_session() returns after a timeout once no further input_prompt events arrive."""
    user = MagicMock()
    user.pk = 1
    prompt = MooPrompt(user)

    req = {
        "prompt": "Old password: ",
        "password": True,
        "caller_id": 1,
        "player_id": 1,
        "callback_this_id": 10,
        "callback_verb_name": "at_password_new",
        "args": [],
    }

    class _MockSession:
        def __init__(self, *a, **kw):
            pass

        async def prompt_async(self, *a, **kw):  # pylint: disable=unused-argument
            return "whatever"

    async def _fake_wait_for(coro, timeout):  # pylint: disable=unused-argument
        coro.close()
        raise asyncio.TimeoutError()

    wizard_caller = MagicMock()
    wizard_caller.is_wizard.return_value = True
    with (
        patch("moo.shell.prompt.PromptSession", _MockSession),
        patch("moo.shell.prompt.models.Object.objects.get", return_value=wizard_caller),
        patch("moo.shell.prompt.tasks.invoke_verb") as mock_task,
        patch("moo.shell.prompt.asyncio.wait_for", side_effect=_fake_wait_for),
    ):
        asyncio.run(prompt.run_input_session(req))
    # Exactly one delay → after the first prompt the queue-wait timed out and
    # the session exited normally rather than showing another prompt.
    assert mock_task.delay.call_count == 1
