# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for moo.shell.server — SSH session lifecycle and authentication logic.

Tests that require a live asyncssh server (interact, server()) are excluded;
the testable surface is MooPromptToolkitSSHSession, SSHServer auth methods,
and session_requested().
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from prompt_toolkit.contrib.ssh import PromptToolkitSSHSession

from moo.shell.server import MooPromptToolkitSSHSession, SSHServer

User = get_user_model()

# ---------------------------------------------------------------------------
# SSHServer.validate_password() — password authentication logic
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_validate_password_correct():
    """validate_password returns True and sets server.user when password is correct."""
    user = User.objects.create_user(username="testpwuser", password="correct-pass")
    server = SSHServer.__new__(SSHServer)

    result = asyncio.run(server.validate_password("testpwuser", "correct-pass"))

    assert result is True
    assert server.user == user


@pytest.mark.django_db(transaction=True)
def test_validate_password_incorrect():
    """validate_password returns False when the password is wrong."""
    User.objects.create_user(username="testpwuser2", password="correct-pass")
    server = SSHServer.__new__(SSHServer)

    result = asyncio.run(server.validate_password("testpwuser2", "wrong-pass"))

    assert result is False


@pytest.mark.django_db(transaction=True)
def test_validate_password_nonexistent_user():
    """validate_password returns False (not an exception) for an unknown username.

    Previously User.objects.get() raised User.DoesNotExist which bubbled up
    through the asyncssh auth handler and could leave the server in a bad state.
    """
    server = SSHServer.__new__(SSHServer)

    result = asyncio.run(server.validate_password("no-such-user", "any-pass"))

    assert result is False


# ---------------------------------------------------------------------------
# SSHServer.session_requested() — session factory
# ---------------------------------------------------------------------------


def test_session_requested_sets_user():
    """session_requested() returns a MooPromptToolkitSSHSession with user assigned."""
    server = SSHServer.__new__(SSHServer)
    server.interact = MagicMock()
    server.enable_cpr = True
    server.user = MagicMock()

    session = server.session_requested()

    assert isinstance(session, MooPromptToolkitSSHSession)
    assert session.user is server.user


# ---------------------------------------------------------------------------
# MooPromptToolkitSSHSession.session_started() — TERM-driven mode detection
# ---------------------------------------------------------------------------


def _make_session_with_term(term: str) -> MooPromptToolkitSSHSession:
    """Build a bare session with a channel that reports the given TERM string."""
    session = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    session._chan = MagicMock()
    session._chan.get_terminal_type.return_value = term
    session.enable_cpr = True
    return session


def test_session_started_default_term_is_rich_mode():
    """A normal terminal (e.g. xterm-256color) produces rich mode with no automation."""
    session = _make_session_with_term("xterm-256color")
    with patch.object(PromptToolkitSSHSession, "session_started"):
        session.session_started()
    assert session.mode == "rich"
    assert session.is_automation is False


def test_session_started_xterm_256_basic_sets_raw_mode():
    """TERM=xterm-256-basic selects raw mode; whitespace and case are tolerated."""
    for term in ("xterm-256-basic", "  XTERM-256-BASIC  "):
        session = _make_session_with_term(term)
        with patch.object(PromptToolkitSSHSession, "session_started"):
            session.session_started()
        assert session.mode == "raw", term
        assert session.is_automation is False


def test_session_started_moo_automation_stays_rich():
    """TERM containing moo-automation stays in rich mode with is_automation=True and CPR disabled."""
    session = _make_session_with_term("moo-automation-v1")
    with patch.object(PromptToolkitSSHSession, "session_started"):
        session.session_started()
    assert session.mode == "rich"
    assert session.is_automation is True
    assert session.enable_cpr is False
