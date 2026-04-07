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
