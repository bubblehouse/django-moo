# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for the windowed-display mode:

- ``WindowState`` grid/scroll model (write/overwrite, cursor+emit, clear,
  resize, scroll tail).
- ``build_window_app`` construction smoke test.
- ``MooPrompt.run_window_session`` callback dispatch + lifecycle flag.
- ``MooPrompt._route_window_event`` mutations + raw-mode no-op.
- editor/paginator rejection while a window is active.
- ``MooPrompt._window_append`` output reroute.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import moo.shell.prompt as prompt_module
from moo.shell.prompt import MODE_RAW, MooPrompt
from moo.shell.window import WindowState, build_window_app


@pytest.fixture(autouse=True)
def _clean_session_settings():
    prompt_module._session_settings.clear()
    yield
    prompt_module._session_settings.clear()


# ---------------------------------------------------------------------------
# WindowState
# ---------------------------------------------------------------------------


def test_windowstate_write_positions_by_column():
    state = WindowState(height=2)
    state.write(0, 0, "AB")
    state.write(1, 3, "X")
    lines = state.render_top().split("\n")
    assert "AB" in lines[0]
    assert "   X" in lines[1]


def test_windowstate_write_overwrites_same_cell():
    state = WindowState(height=1)
    state.write(0, 0, "old")
    state.write(0, 0, "new")
    top = state.render_top()
    assert "new" in top
    assert "old" not in top


def test_windowstate_cursor_emit_advances():
    state = WindowState(height=1)
    state.move_cursor(0, 2)
    state.emit("Hi")
    assert state.cursor == (0, 4)
    assert "Hi" in state.render_top()


def test_windowstate_emit_wraps_on_newline():
    state = WindowState(height=2)
    state.move_cursor(0, 0)
    state.emit("a\nb")
    assert state.cursor == (1, 1)
    lines = state.render_top().split("\n")
    assert "a" in lines[0]
    assert "b" in lines[1]


def test_windowstate_clear_row_then_all():
    state = WindowState(height=2)
    state.write(0, 0, "A")
    state.write(1, 0, "B")
    state.clear(0)
    assert "A" not in state.render_top()
    assert "B" in state.render_top()
    state.clear()
    assert "B" not in state.render_top()


def test_windowstate_set_height_resizes_render():
    state = WindowState(height=1)
    state.set_height(5)
    assert state.height == 5
    assert len(state.render_top().split("\n")) == 5


def test_windowstate_scroll_returns_tail():
    state = WindowState(height=1)
    for i in range(10):
        state.append_output(f"line{i}")
    out = state.render_scroll(3)
    assert "line9" in out
    assert "line7" in out
    assert "line6" not in out


def test_windowstate_append_splits_lines():
    state = WindowState(height=1)
    state.append_output("one\ntwo")
    assert list(state.scroll_lines) == ["one", "two"]


# ---------------------------------------------------------------------------
# build_window_app
# ---------------------------------------------------------------------------


def test_build_window_app_constructs():
    state = WindowState(height=2, title="T")
    app = build_window_app(state, lambda buff: False)
    assert app is not None
    assert hasattr(app, "window_input_area")


# ---------------------------------------------------------------------------
# run_window_session
# ---------------------------------------------------------------------------


def _user(pk=7000):
    user = MagicMock()
    user.pk = pk
    return user


def _window_req(**overrides):
    req = {
        "height": 3,
        "title": "Demo",
        "caller_id": 1,
        "player_id": 2,
        "callback_this_id": 3,
        "callback_verb_name": "on_close",
        "args": ["x"],
    }
    req.update(overrides)
    return req


def test_run_window_session_dispatches_callback_and_clears_state():
    prompt = MooPrompt(_user())
    mock_app = MagicMock()
    mock_app.run_async = AsyncMock()
    wizard = MagicMock()
    wizard.is_wizard.return_value = True
    with patch("moo.shell.window.build_window_app", return_value=mock_app):
        with patch("moo.shell.prompt.models.Object.objects.get", return_value=wizard):
            with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
                asyncio.run(prompt.run_window_session(_window_req()))
    mock_task.delay.assert_called_once_with(
        "closed",
        "x",
        caller_id=1,
        player_id=2,
        this_id=3,
        verb_name="on_close",
    )
    assert prompt._window_app is None
    assert prompt._window_state is None
    assert prompt_module._session_settings[prompt.user.pk]["window_active"] is False


def test_run_window_session_rejects_non_wizard_caller():
    prompt = MooPrompt(_user())
    mock_app = MagicMock()
    mock_app.run_async = AsyncMock()
    non_wizard = MagicMock()
    non_wizard.is_wizard.return_value = False
    with patch("moo.shell.window.build_window_app", return_value=mock_app):
        with patch("moo.shell.prompt.models.Object.objects.get", return_value=non_wizard):
            with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
                asyncio.run(prompt.run_window_session(_window_req(caller_id=99)))
    mock_task.delay.assert_not_called()


def test_run_window_session_no_callback_without_fields():
    prompt = MooPrompt(_user())
    mock_app = MagicMock()
    mock_app.run_async = AsyncMock()
    with patch("moo.shell.window.build_window_app", return_value=mock_app):
        with patch("moo.shell.prompt.tasks.invoke_verb") as mock_task:
            asyncio.run(prompt.run_window_session({"height": 2}))
    mock_task.delay.assert_not_called()


# ---------------------------------------------------------------------------
# _route_window_event
# ---------------------------------------------------------------------------


def _prompt_in_window(height=2):
    prompt = MooPrompt(MagicMock())
    prompt._window_state = WindowState(height=height)
    prompt._window_app = MagicMock()
    return prompt


def test_route_window_event_write_mutates_and_invalidates():
    prompt = _prompt_in_window()
    prompt._route_window_event("window_write", {"event": "window_write", "row": 0, "col": 0, "text": "Z"})
    assert "Z" in prompt._window_state.render_top()
    prompt._window_app.invalidate.assert_called()


def test_route_window_event_split_resizes():
    prompt = _prompt_in_window()
    prompt._route_window_event("window_split", {"event": "window_split", "height": 7})
    assert prompt._window_state.height == 7


def test_route_window_event_close_exits_app():
    prompt = _prompt_in_window()
    prompt._route_window_event("window_close", {"event": "window_close"})
    prompt._window_app.exit.assert_called_once()


def test_route_window_event_open_queues_when_inactive():
    prompt = MooPrompt(MagicMock())
    prompt._route_window_event("window_open", {"event": "window_open", "height": 4})
    assert not prompt.window_queue.empty()


def test_route_window_event_noop_in_raw_mode():
    prompt = MooPrompt(MagicMock(), mode=MODE_RAW)
    prompt._route_window_event("window_open", {"event": "window_open", "height": 2})
    assert prompt.window_queue.empty()


# ---------------------------------------------------------------------------
# editor/paginator rejection while window active
# ---------------------------------------------------------------------------


def test_route_event_rejects_editor_in_window_mode():
    prompt = _prompt_in_window()
    asyncio.run(prompt._route_event({"event": "editor", "content": "x"}))
    assert prompt.editor_queue.empty()
    assert any("not available" in line for line in prompt._window_state.scroll_lines)


# ---------------------------------------------------------------------------
# _window_append (process_messages reroute)
# ---------------------------------------------------------------------------


def test_window_append_routes_output_to_scroll():
    prompt = _prompt_in_window()
    prompt._window_append(["[bold]hi[/bold]", "there"], quiet=False)
    joined = "\n".join(prompt._window_state.scroll_lines)
    assert "hi" in joined
    assert "there" in joined
    prompt._window_app.invalidate.assert_called()
