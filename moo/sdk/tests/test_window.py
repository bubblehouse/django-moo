# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for the windowed-display SDK functions in ``moo.sdk.output``:

- ``open_window`` / ``window_write`` / ``window_cursor`` / ``window_emit`` /
  ``window_clear`` / ``window_split`` / ``close_window`` — broker event shape +
  wizard gating + the GMCP ``Window.*`` mirror.
- ``window_supported`` — rich-mode gating.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import moo.shell.prompt as prompt_module
from moo.core import code as core_code
from moo.core.exceptions import UserError
from moo.sdk import output


def _wizard():
    return SimpleNamespace(is_wizard=lambda: True, pk=1)


def _mortal():
    return SimpleNamespace(is_wizard=lambda: False, pk=2)


@pytest.fixture(autouse=True)
def _clean_session_settings():
    prompt_module._session_settings.clear()
    yield
    prompt_module._session_settings.clear()


# ---------------------------------------------------------------------------
# Event publication (GMCP off)
# ---------------------------------------------------------------------------


def _publish_for(fn, *args, **kwargs):
    """Call ``fn`` as a wizard with GMCP disabled; return the published events."""
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", return_value=False):
            with patch("moo.core._publish_to_player") as pub:
                fn(MagicMock(), *args, **kwargs)
    return [call.args[1] for call in pub.call_args_list]


def test_open_window_publishes_window_open():
    events = _publish_for(output.open_window, height=5, title="Map")
    assert len(events) == 1
    msg = events[0]
    assert msg["event"] == "window_open"
    assert msg["height"] == 5
    assert msg["title"] == "Map"
    assert msg["caller_id"] == 1
    assert msg["callback_this_id"] is None


def test_window_write_publishes_event():
    events = _publish_for(output.window_write, 2, 3, "[bold]X[/bold]")
    assert events == [{"event": "window_write", "row": 2, "col": 3, "text": "[bold]X[/bold]"}]


def test_window_cursor_publishes_event():
    events = _publish_for(output.window_cursor, 1, 4)
    assert events == [{"event": "window_cursor", "row": 1, "col": 4}]


def test_window_emit_publishes_event():
    events = _publish_for(output.window_emit, "hi")
    assert events == [{"event": "window_emit", "text": "hi"}]


def test_window_clear_whole_and_row():
    events = _publish_for(output.window_clear)
    assert events == [{"event": "window_clear", "row": None}]
    events = _publish_for(output.window_clear, 2)
    assert events == [{"event": "window_clear", "row": 2}]


def test_window_split_publishes_event():
    events = _publish_for(output.window_split, 12)
    assert events == [{"event": "window_split", "height": 12}]


def test_close_window_publishes_event():
    events = _publish_for(output.close_window)
    assert events == [{"event": "window_close"}]


# ---------------------------------------------------------------------------
# Wizard gating
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda: output.open_window(MagicMock()),
        lambda: output.window_write(MagicMock(), 0, 0, "x"),
        lambda: output.window_cursor(MagicMock(), 0, 0),
        lambda: output.window_emit(MagicMock(), "x"),
        lambda: output.window_clear(MagicMock()),
        lambda: output.window_split(MagicMock(), 1),
        lambda: output.close_window(MagicMock()),
    ],
)
def test_window_functions_reject_non_wizard(call):
    with core_code.ContextManager(_mortal(), lambda s: None):
        with pytest.raises(UserError, match="wizards"):
            call()


# ---------------------------------------------------------------------------
# GMCP mirror (negotiated clients)
# ---------------------------------------------------------------------------


def test_open_window_sends_gmcp_when_negotiated():
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", return_value=True):
            with patch("moo.core._publish_to_player") as pub:
                output.open_window(obj, height=3, title="HUD")
    events = [call.args[1] for call in pub.call_args_list]
    assert any(e.get("event") == "window_open" for e in events)
    oob = [e for e in events if e.get("event") == "oob"]
    assert oob, "expected a GMCP oob frame"
    assert b"Window.Open" in oob[0]["data"]


def test_window_write_gmcp_cell_strips_markup():
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", return_value=True):
            with patch("moo.core._publish_to_player") as pub:
                output.window_write(obj, 1, 2, "[bold]Hi[/bold]")
    oob = [call.args[1] for call in pub.call_args_list if call.args[1].get("event") == "oob"]
    assert oob
    data = oob[0]["data"]
    assert b"Window.Cell" in data
    assert b"Hi" in data
    assert b"bold" not in data  # GMCP payload is plain text


# ---------------------------------------------------------------------------
# window_supported
# ---------------------------------------------------------------------------


def test_window_supported_true_in_rich_mode():
    with patch("moo.sdk.output.get_client_mode", return_value="rich"):
        assert output.window_supported() is True


def test_window_supported_false_in_raw_mode():
    with patch("moo.sdk.output.get_client_mode", return_value="raw"):
        assert output.window_supported() is False
