# -*- coding: utf-8 -*-

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from prompt_toolkit import ANSI

from moo.shell.prompt import MooPrompt


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_init():
    """MooPrompt initialises with correct default state and async queues."""
    user = MagicMock()
    prompt = MooPrompt(user)
    assert prompt.user is user
    assert prompt.is_exiting is False
    assert isinstance(prompt.editor_queue, asyncio.Queue)
    assert isinstance(prompt.paginator_queue, asyncio.Queue)


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
    with patch("moo.shell.editor.run_editor", new=AsyncMock(return_value="edited text")):
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
