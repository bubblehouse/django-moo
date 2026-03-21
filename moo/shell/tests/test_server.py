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

from moo.shell.server import MooPromptToolkitSSHSession, SSHServer

User = get_user_model()

# ---------------------------------------------------------------------------
# MooPromptToolkitSSHSession.session_started() — automation detection
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
