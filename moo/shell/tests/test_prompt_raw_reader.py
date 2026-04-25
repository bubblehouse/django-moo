# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for MooPrompt._read_line_raw — the raw-mode line reader.

The real implementation reads keys from prompt_toolkit's ``Input`` abstraction
wired up by the contrib SSH session. Here we stub that abstraction: a fake
Input returns scripted KeyPress sequences, and we assert the reader buffers,
echoes, and terminates as expected.
"""

import asyncio
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys

from moo.shell.prompt import MODE_RAW, MooPrompt


class _FakeInput:
    """Stand-in for prompt_toolkit's Input that yields scripted key batches."""

    def __init__(self, batches):
        # batches: list of lists of KeyPress (each inner list = one read_keys() call)
        self._batches = list(batches)

    @contextmanager
    def raw_mode(self):
        yield

    def attach(self, callback):
        @contextmanager
        def _ctx():
            yield

        return _ctx()

    def read_keys(self):
        if not self._batches:
            return []
        return self._batches.pop(0)


def _make_prompt():
    user = MagicMock()
    session = MagicMock()
    return MooPrompt(user, session=session, mode=MODE_RAW)


def _run_reader(prompt, input_obj):
    sess = MagicMock()
    sess.input = input_obj
    with patch("prompt_toolkit.application.current.get_app_session", return_value=sess):
        return asyncio.run(prompt._read_line_raw())


def test_read_line_raw_returns_line_without_crlf():
    """A sequence of character keys followed by Enter yields the decoded line without CR/LF."""
    prompt = _make_prompt()
    batches = [
        [
            KeyPress("h", "h"),
            KeyPress("i", "i"),
            KeyPress(Keys.ControlM, "\r"),
        ],
    ]
    result = _run_reader(prompt, _FakeInput(batches))
    assert result == "hi"


def test_read_line_raw_handles_partial_chunks():
    """Characters delivered across multiple read_keys() calls still produce one line."""
    prompt = _make_prompt()
    batches = [
        [KeyPress("h", "h"), KeyPress("e", "e")],
        [KeyPress("l", "l"), KeyPress("l", "l"), KeyPress("o", "o")],
        [KeyPress(Keys.ControlJ, "\n")],
    ]
    result = _run_reader(prompt, _FakeInput(batches))
    assert result == "hello"


def test_read_line_raw_yields_none_on_eof():
    """Ctrl-D on an empty buffer signals EOF and returns None."""
    prompt = _make_prompt()
    batches = [[KeyPress(Keys.ControlD, "\x04")]]
    result = _run_reader(prompt, _FakeInput(batches))
    assert result is None


def test_read_line_raw_does_not_echo_input_back_to_channel():
    """
    Server-side echo would land as a duplicate copy in MUD clients that
    local-echo (Mudlet, MUSHclient, TinTin++). The raw reader must stay
    silent on the channel and let the client display its own input.
    """
    prompt = _make_prompt()
    batches = [
        [
            KeyPress("h", "h"),
            KeyPress("i", "i"),
            KeyPress(Keys.ControlM, "\r"),
        ],
    ]
    _run_reader(prompt, _FakeInput(batches))
    # _chan_write should never have been called from inside _read_line_raw.
    prompt._chan.write.assert_not_called()
