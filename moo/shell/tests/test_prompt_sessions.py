# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for the prompt's interactive sub-sessions.

Covers:
  - the GMCP ``Editor.Start`` handoff path (`_try_gmcp_editor_handoff`)
    and how `_route_event` chooses between handoff and the prompt-toolkit
    fallback
  - run_editor_session callback dispatch (wizard-only, cancellation,
    missing callback fields)
  - run_paginator_session
  - the raw-mode editor rejection text
  - run_input_session: chained password prompts and timeout exit
"""

import asyncio
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


def _editor_message(content="print('hi')\n", **overrides):
    """Build the dict-shape that ``_route_event`` receives for an "editor" event."""
    msg = {
        "event": "editor",
        "content": content,
        "content_type": "python",
        "title": "test edit",
        "args": ["arg1"],
        "callback_this_id": 42,
        "callback_verb_name": "@edit",
        "caller_id": 7,
        "player_id": 7,
    }
    msg.update(overrides)
    return msg


# ---------------------------------------------------------------------------
# _try_gmcp_editor_handoff — bridge-to-Mudlet flow
# ---------------------------------------------------------------------------


def test_gmcp_editor_handoff_noop_when_user_missing():
    """No user → no handoff. The prompt-toolkit fallback path takes over."""
    user = MagicMock()
    user.pk = 5000
    session = MagicMock()
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    # MooPrompt's constructor requires a user.pk to seed _session_settings,
    # but the handoff method itself defends against ``self.user is None``.
    prompt.user = None
    assert prompt._try_gmcp_editor_handoff(_editor_message()) is False
    session._chan.write.assert_not_called()


def test_gmcp_editor_handoff_skipped_when_editor_package_not_advertised():
    """A client that never sent ``Core.Supports.Set [Editor 1]`` falls through to the TUI editor."""
    user = MagicMock()
    user.pk = 5001
    session = MagicMock()
    session.iac_enabled = True
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    # GMCP negotiated, but no Editor package in the supports map.
    prompt_module._session_settings.setdefault(user.pk, {})["iac"] = {"gmcp_packages": {"Char": 1}}

    assert prompt._try_gmcp_editor_handoff(_editor_message()) is False
    session._chan.write.assert_not_called()
    # Pending edits dict is not created on miss.
    assert "pending_edits" not in prompt_module._session_settings[user.pk]


def test_gmcp_editor_handoff_writes_editor_start_and_stashes_pending():
    """
    Successful handoff: the GMCP ``Editor.Start`` frame goes to the channel,
    the callback metadata is stashed under the generated edit id, and the
    return value tells the caller to NOT also enqueue the prompt-toolkit
    fallback.
    """
    from moo.shell.iac import IAC, OPT_GMCP, SB, SE

    user = MagicMock()
    user.pk = 5002
    session = MagicMock()
    session.iac_enabled = True
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    prompt_module._session_settings.setdefault(user.pk, {})["iac"] = {"gmcp_packages": {"Editor": 1}}

    msg = _editor_message(content="print('hello')\n", title="custom title")
    assert prompt._try_gmcp_editor_handoff(msg) is True

    # Frame on the wire: IAC SB GMCP "Editor.Start <json>" IAC SE.
    session._chan.write.assert_called_once()
    written = session._chan.write.call_args[0][0]
    raw = written.encode("utf-8", errors="surrogateescape")
    assert raw.startswith(bytes((IAC, SB, OPT_GMCP)))
    assert raw.endswith(bytes((IAC, SE)))
    assert b"Editor.Start" in raw
    assert b"print('hello')" in raw
    assert b"custom title" in raw

    # Pending edit recorded under the generated id; metadata round-trips.
    pending = prompt_module._session_settings[user.pk]["pending_edits"]
    assert len(pending) == 1
    edit_id, entry = next(iter(pending.items()))
    assert b'"id":"' + edit_id.encode() + b'"' in raw
    assert entry["callback_this_id"] == 42
    assert entry["callback_verb_name"] == "@edit"
    assert entry["caller_id"] == 7
    assert entry["player_id"] == 7
    assert entry["args"] == ["arg1"]


def test_gmcp_editor_handoff_rolls_back_pending_on_send_failure():
    """
    If writing the ``Editor.Start`` frame raises, the pending entry is
    removed so a future ``Editor.Save`` from a stale id cannot dispatch a
    callback that the client never actually started.
    """
    user = MagicMock()
    user.pk = 5003
    session = MagicMock()
    session.iac_enabled = True
    session._chan.write.side_effect = OSError("connection reset")
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    prompt_module._session_settings.setdefault(user.pk, {})["iac"] = {"gmcp_packages": {"Editor": 1}}

    assert prompt._try_gmcp_editor_handoff(_editor_message()) is False
    # No leaked pending entry — the dict should be empty (it may have been
    # created but the failed entry was popped).
    pending = prompt_module._session_settings[user.pk].get("pending_edits", {})
    assert pending == {}


def test_route_event_editor_returns_early_when_gmcp_handoff_succeeds():
    """
    When ``_try_gmcp_editor_handoff`` reports success, ``_route_event`` must
    NOT also enqueue the editor message — otherwise the prompt-toolkit TUI
    would open over top of the bridge editor.
    """
    user = MagicMock()
    user.pk = 5005
    session = MagicMock()
    session.iac_enabled = True
    prompt = MooPrompt(user, session=session, mode=MODE_RAW)
    prompt_module._session_settings.setdefault(user.pk, {})["iac"] = {"gmcp_packages": {"Editor": 1}}

    asyncio.run(prompt._route_event(_editor_message()))
    # Wire write happened (the GMCP frame), but nothing landed on the queue.
    session._chan.write.assert_called_once()
    assert prompt.editor_queue.empty()


def test_route_event_editor_falls_back_to_queue_when_no_gmcp_bridge():
    """
    When the GMCP handoff returns False (no bridge), ``_route_event`` must
    push the editor message onto the queue so the prompt-toolkit TUI editor
    can pick it up — the existing behaviour for vanilla SSH clients.
    """
    user = MagicMock()
    user.pk = 5004
    session = MagicMock()
    prompt = MooPrompt(user, session=session, mode=MODE_RICH)

    async def _run():
        # No iac/gmcp_packages → handoff returns False.
        await prompt._route_event(_editor_message())
        return await prompt.editor_queue.get()

    queued = asyncio.run(_run())
    assert queued["event"] == "editor"
    assert queued["content"] == "print('hi')\n"


# ---------------------------------------------------------------------------
# run_editor_session
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# run_paginator_session
# ---------------------------------------------------------------------------


def test_run_paginator_session():
    """run_paginator_session() delegates to run_paginator with content and content_type."""
    prompt = MooPrompt(MagicMock())
    req = {"content": "page text", "content_type": "python"}
    with patch("moo.shell.paginator.run_paginator", new=AsyncMock()) as mock_paginator:
        asyncio.run(prompt.run_paginator_session(req))
    mock_paginator.assert_called_once_with("page text", "python")


# ---------------------------------------------------------------------------
# Raw-mode editor rejection
# ---------------------------------------------------------------------------


def test_raw_editor_event_emits_rejection_text():
    """An editor request in raw mode is refused with the inline-form hint."""
    user = MagicMock()
    prompt = MooPrompt(user, session=MagicMock(), mode=MODE_RAW)
    pieces = prompt._editor_rejection_pieces()
    assert any("@edit" in p and "with" in p for p in pieces)


# ---------------------------------------------------------------------------
# run_input_session — chained inline prompts
# ---------------------------------------------------------------------------


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
