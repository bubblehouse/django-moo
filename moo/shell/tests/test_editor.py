# -*- coding: utf-8 -*-

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from moo.core import code
from moo.sdk import create, lookup, open_editor
from moo.core.exceptions import UserError
from moo.core.models import Object

# ---------------------------------------------------------------------------
# Helper verb bodies
# ---------------------------------------------------------------------------

# Trigger verb: opens an editor pre-filled with "hello\nworld", wiring the
# callback verb on the same object to receive the saved text.
_TRIGGER_VERB = """\
from moo.sdk import context, open_editor
callback = this.get_verb("edit_callback")
open_editor(context.player, "hello\\nworld", callback)
"""

# Trigger verb variant that passes content_type="python".
_TRIGGER_VERB_PYTHON = """\
from moo.sdk import context, open_editor
callback = this.get_verb("edit_callback")
open_editor(context.player, "def foo():\\n    pass", callback, content_type="python")
"""

# Trigger verb variant that passes extra args to the callback.
_TRIGGER_VERB_EXTRA_ARGS = """\
from moo.sdk import context, open_editor
callback = this.get_verb("edit_callback")
open_editor(context.player, "hello\\nworld", callback, "extra1", 42)
"""

# Callback verb: receives the edited text as args[0] and prints it.
_CALLBACK_VERB = "print(args[0])"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_publishes_editor_event(t_init: Object, t_wizard: Object):
    """Invoking a verb that calls open_editor() publishes an editor event dict
    to the player's Kombu queue (emitted as a RuntimeWarning in tests)."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test", parents=[t_init.root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        obj.add_verb("trigger_edit", code=_TRIGGER_VERB)

        with pytest.warns(RuntimeWarning) as w:
            obj.invoke_verb("trigger_edit")

    messages = [str(warning.message) for warning in w.list]
    assert any("'event': 'editor'" in m for m in messages)
    assert any("hello" in m for m in messages)
    assert any("edit_callback" in m for m in messages)
    assert any("'content_type': 'text'" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_python_content_type(t_init: Object, t_wizard: Object):
    """content_type='python' is passed through to the editor event dict."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test_py", parents=[t_init.root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        obj.add_verb("trigger_edit", code=_TRIGGER_VERB_PYTHON)

        with pytest.warns(RuntimeWarning) as w:
            obj.invoke_verb("trigger_edit")

    messages = [str(warning.message) for warning in w.list]
    assert any("'content_type': 'python'" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_extra_args_forwarded(t_init: Object, t_wizard: Object):
    """Extra positional args to open_editor() appear in the editor event dict."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test_args", parents=[t_init.root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        obj.add_verb("trigger_edit", code=_TRIGGER_VERB_EXTRA_ARGS)

        with pytest.warns(RuntimeWarning) as w:
            obj.invoke_verb("trigger_edit")

    messages = [str(warning.message) for warning in w.list]
    assert any("extra1" in m for m in messages)
    assert any("42" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_invalid_content_type_raises(t_init: Object, t_wizard: Object):
    """open_editor() raises UserError for an unrecognised content_type."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test_err", parents=[t_init.root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        callback = obj.get_verb("edit_callback")

        with pytest.raises(UserError):
            open_editor(t_wizard, "some text", callback, content_type="xml")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_non_wizard_raises(t_init: Object, t_wizard: Object):
    """open_editor() raises UserError when the caller is not a wizard."""
    player_npc = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test_perm", parents=[t_init.root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        callback = obj.get_verb("edit_callback")

    # Re-enter as the non-wizard player
    with code.ContextManager(player_npc, lambda _: None):
        with pytest.raises(UserError):
            open_editor(player_npc, "some text", callback)


# ---------------------------------------------------------------------------
# run_editor() — key binding state machine and lexer branching
#
# Strategy: patch Application so run_async() fires real key handlers
# (which close over the real `state` and `result` dicts), then assert on
# the return value.
# ---------------------------------------------------------------------------


def _run_with_key_sequence(initial_text, key_sequence, content_type="text"):
    """
    Run run_editor() with a mocked Application whose run_async fires the
    given key handlers in order.  Returns the return value of run_editor().
    """
    from moo.shell.editor import run_editor

    kb_capture = []

    async def fake_run_async():
        kb = kb_capture[0]
        event = MagicMock()
        for key in key_sequence:
            binding = next((b for b in kb.bindings if key in b.keys), None)
            if binding:
                binding.handler(event)

    mock_app = MagicMock()
    mock_app.run_async = fake_run_async

    with patch("moo.shell.editor.Application") as MockApp:

        def capture_app(**kwargs):
            kb_capture.append(kwargs["key_bindings"])
            return mock_app

        MockApp.side_effect = capture_app
        return asyncio.run(run_editor(initial_text, content_type=content_type))


def test_run_editor_no_save_returns_none():
    """run_editor returns None when no key is pressed (application exits without saving)."""
    from moo.shell.editor import run_editor

    mock_app = MagicMock()
    mock_app.run_async = AsyncMock()

    with patch("moo.shell.editor.Application", return_value=mock_app):
        result = asyncio.run(run_editor("hello", content_type="text"))

    assert result is None


def test_run_editor_python_lexer_branch():
    """content_type='python' triggers the lexer lookup branch without error."""
    from moo.shell.editor import run_editor

    mock_app = MagicMock()
    mock_app.run_async = AsyncMock()

    with patch("moo.shell.editor.Application", return_value=mock_app):
        result = asyncio.run(run_editor("def foo(): pass", content_type="python"))

    assert result is None  # no save


def test_run_editor_save_flow():
    """Ctrl+S then Y saves the buffer and returns the initial text."""
    result = _run_with_key_sequence("hello world", ["c-s", "y"])
    assert result == "hello world"


def test_run_editor_cancel_flow():
    """Ctrl+C then Y cancels without saving and returns None."""
    result = _run_with_key_sequence("hello world", ["c-c", "y"])
    assert result is None


def test_run_editor_deny_resets_state():
    """Ctrl+S then N resets confirming state; subsequent Ctrl+C then Y cancels."""
    # Start save, deny it, then cancel — should return None (no save completed)
    result = _run_with_key_sequence("hello world", ["c-s", "n", "c-c", "y"])
    assert result is None


def test_run_editor_get_status_text():
    """get_status_text returns the correct prompt for each confirming state."""
    from moo.shell.editor import run_editor

    status_fn_ref = []

    mock_app = MagicMock()
    mock_app.run_async = AsyncMock()

    with (
        patch("moo.shell.editor.Application", return_value=mock_app),
        patch("moo.shell.editor.FormattedTextControl") as MockFmtCtrl,
    ):
        MockFmtCtrl.side_effect = lambda fn: status_fn_ref.append(fn) or MagicMock()
        asyncio.run(run_editor("x"))

    get_status_text = status_fn_ref[0]
    assert get_status_text() == "[Ctrl+S] Save  [Ctrl+C/Q] Cancel"
