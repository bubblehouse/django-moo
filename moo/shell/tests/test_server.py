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


# ---------------------------------------------------------------------------
# MooPromptToolkitSSHSession — IAC integration
# ---------------------------------------------------------------------------


def test_is_mud_term_recognizes_known_clients_and_raw_opt_in():
    """The TERM heuristic gates everything IAC-related."""
    from moo.shell.server import _is_mud_term

    assert _is_mud_term("xterm-256-basic")
    assert _is_mud_term("MUDLET")
    assert _is_mud_term("tintin++")
    assert _is_mud_term("mushclient-1.4")
    assert not _is_mud_term("xterm-256color")
    assert not _is_mud_term("vt100")
    assert not _is_mud_term(None)
    assert not _is_mud_term("")


def test_session_started_emits_iac_only_for_mud_clients():
    """xterm-256-basic opts into IAC; vanilla xterm leaves the channel untouched."""
    from moo.shell.iac import DO, IAC, OPT_GMCP, OPT_TTYPE, IacNegotiator, IacParser, WILL

    # MUD-client TERM → offers go out as surrogate-escape str.
    session = _make_session_with_term("xterm-256-basic")
    session.iac_parser = IacParser()
    session.iac_negotiator = IacNegotiator()
    session.iac_enabled = True
    with patch.object(PromptToolkitSSHSession, "session_started"):
        session.session_started()
    written = "".join(call.args[0] for call in session._chan.write.call_args_list if call.args)
    written_bytes = written.encode("utf-8", errors="surrogateescape")
    assert bytes((IAC, WILL, OPT_GMCP)) in written_bytes
    assert bytes((IAC, DO, OPT_TTYPE)) in written_bytes

    # Vanilla xterm → no IAC bytes anywhere on the channel.
    plain = _make_session_with_term("xterm-256color")
    plain.iac_parser = IacParser()
    plain.iac_negotiator = IacNegotiator()
    plain.iac_enabled = False
    with patch.object(PromptToolkitSSHSession, "session_started"):
        plain.session_started()
    assert plain._chan.write.call_count == 0


def test_session_started_automation_skips_iac():
    """Automation sessions skip IAC negotiation because clients cannot round-trip 0xFF."""
    from moo.shell.iac import IacNegotiator, IacParser

    session = _make_session_with_term("moo-automation-v1")
    session.iac_parser = IacParser()
    session.iac_negotiator = IacNegotiator()
    session.iac_enabled = False  # moo-automation TERM is not a MUD client
    with patch.object(PromptToolkitSSHSession, "session_started"):
        session.session_started()
    assert session._chan.write.call_count == 0


def test_session_started_clears_stale_iac_cache_for_vanilla_term():
    """A vanilla SSH session must wipe any leftover iac cache from a previous MUD-client session."""
    from django.core.cache import cache

    from moo.shell.iac import IacNegotiator, IacParser
    from moo.shell.prompt import _session_settings

    user = MagicMock()
    user.pk = 7777
    # Simulate stale state from a prior MUD-client session.
    _session_settings.setdefault(user.pk, {})["iac"] = {"gmcp": True}
    cache.set(f"moo:session:{user.pk}:iac", {"gmcp": True}, timeout=86400)

    session = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    session.iac_parser = IacParser()
    session.iac_negotiator = IacNegotiator()
    session.enable_cpr = True
    session.stdout = MagicMock()
    session.user = user
    session._chan = MagicMock()
    session._chan.get_terminal_type.return_value = "xterm-256color"

    try:
        with patch.object(PromptToolkitSSHSession, "session_started"):
            session.session_started()
        assert session.iac_enabled is False
        assert "iac" not in _session_settings.get(user.pk, {})
        assert cache.get(f"moo:session:{user.pk}:iac") is None
    finally:
        _session_settings.pop(user.pk, None)
        cache.delete(f"moo:session:{user.pk}:iac")


def test_session_started_switches_encoding_policy_for_mud_clients():
    """
    For MUD-client TERM, session_started flips the channel encoding to
    surrogate-escape UTF-8 so 0xFF IAC bytes round-trip cleanly. Vanilla
    SSH leaves the channel in default strict UTF-8.

    Term-driven setup runs in session_started (not connection_made) because
    asyncssh sets the terminal type from the PTY request, which arrives
    after connection_made and before session_started.
    """
    from moo.shell.iac import IacNegotiator, IacParser

    # Vanilla xterm: encoding stays untouched.
    plain = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    plain.iac_parser = IacParser()
    plain.iac_negotiator = IacNegotiator()
    plain.enable_cpr = True
    plain.stdout = MagicMock()
    plain.user = None
    plain._chan = MagicMock()
    plain._chan.get_terminal_type.return_value = "xterm-256color"
    with patch.object(PromptToolkitSSHSession, "session_started"):
        plain.session_started()
    assert plain.iac_enabled is False
    plain._chan.set_encoding.assert_not_called()

    # MUD client: encoding switches to surrogate-escape UTF-8.
    mud = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    mud.iac_parser = IacParser()
    mud.iac_negotiator = IacNegotiator()
    mud.enable_cpr = True
    mud.stdout = MagicMock()
    mud.user = None
    mud._chan = MagicMock()
    mud._chan.get_terminal_type.return_value = "xterm-256-basic"
    with patch.object(PromptToolkitSSHSession, "session_started"):
        mud.session_started()
    assert mud.iac_enabled is True
    mud._chan.set_encoding.assert_called_once_with("utf-8", errors="surrogateescape")


def test_data_received_strips_iac_and_forwards_residual():
    """
    data_received pulls IAC frames out of the surrogate-escaped str stream and
    forwards plain text to prompt_toolkit's input pipe.
    """
    from moo.shell.iac import IAC, OPT_TTYPE, WILL, IacNegotiator, IacParser

    session = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    session._chan = MagicMock()
    session._input = MagicMock()
    session.iac_parser = IacParser()
    session.iac_negotiator = IacNegotiator()
    session.user = None  # _mirror_capabilities short-circuits on None user
    session.iac_enabled = True

    # Interleave text with IAC WILL TTYPE; deliver as a surrogate-escape str
    # (the form asyncssh hands us when channel encoding errors='surrogateescape').
    raw = b"hi" + bytes((IAC, WILL, OPT_TTYPE)) + b"!"
    session.data_received(raw.decode("utf-8", errors="surrogateescape"), None)

    # Residual "hi!" should reach prompt_toolkit's input pipe.
    assert session._input.send_text.call_args.args[0] == "hi!"
    # Negotiator replied DO TTYPE + TTYPE SEND on the channel.
    assert session._chan.write.called


def _surrogate(data: bytes) -> str:
    """Helper: turn raw IAC bytes into the surrogate-escape str the channel delivers."""
    return data.decode("utf-8", errors="surrogateescape")


def test_data_received_mirrors_capabilities_after_do_gmcp():
    """
    End-to-end: a client that enables GMCP via DO (without running TTYPE)
    should see the ``gmcp`` capability land in _session_settings immediately,
    so Celery verbs picking up the next command see GMCP as available.
    """
    from moo.shell.iac import DO, IAC, OPT_GMCP, IacNegotiator, IacParser
    from moo.shell.prompt import _session_settings

    user = MagicMock()
    user.pk = 9991
    session = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    session._chan = MagicMock()
    session._input = MagicMock()
    session.iac_parser = IacParser()
    session.iac_negotiator = IacNegotiator()
    session.user = user
    session.iac_enabled = True

    try:
        session.data_received(_surrogate(bytes((IAC, DO, OPT_GMCP))), None)
        # Negotiator flipped the gmcp flag.
        assert session.iac_negotiator.capabilities["gmcp"] is True
        # And that flip mirrored into _session_settings without requiring a TTYPE dance.
        assert _session_settings.get(user.pk, {}).get("iac", {}).get("gmcp") is True
    finally:
        _session_settings.pop(user.pk, None)


def test_data_received_full_mtts_negotiation_flow():
    """
    End-to-end dance: client says WILL TTYPE, server asks three times, client
    finishes with an MTTS bitfield. The session's iac capabilities should
    reflect the negotiated state and the final bitfield should mirror out.
    """
    from moo.shell.iac import (
        IAC,
        MTTS_ANSI,
        MTTS_SCREEN_READER,
        MTTS_UTF8,
        OPT_TTYPE,
        SB,
        SE,
        TTYPE_IS,
        WILL,
        IacNegotiator,
        IacParser,
    )
    from moo.shell.prompt import _session_settings

    user = MagicMock()
    user.pk = 9992
    session = MooPromptToolkitSSHSession.__new__(MooPromptToolkitSSHSession)
    session._chan = MagicMock()
    session._input = MagicMock()
    session.iac_parser = IacParser()
    session.iac_negotiator = IacNegotiator(on_ttype=session._on_ttype)
    session.user = user
    session.iac_enabled = True

    def ttype_is(name: bytes) -> str:
        return _surrogate(bytes((IAC, SB, OPT_TTYPE, TTYPE_IS)) + name + bytes((IAC, SE)))

    try:
        # Client offers TTYPE → server DOes and sends SEND.
        session.data_received(_surrogate(bytes((IAC, WILL, OPT_TTYPE))), None)
        # Stage 1, 2, 3.
        session.data_received(ttype_is(b"Mudlet"), None)
        session.data_received(ttype_is(b"XTERM-256COLOR"), None)
        mtts = MTTS_ANSI | MTTS_UTF8 | MTTS_SCREEN_READER
        session.data_received(ttype_is(f"MTTS {mtts}".encode()), None)

        caps = session.iac_negotiator.capabilities
        assert caps["ttype"] is True
        assert caps["client_name"] == "Mudlet"
        assert caps["mtts"] == mtts
        # _session_settings got the final snapshot.
        mirrored = _session_settings.get(user.pk, {}).get("iac", {})
        assert mirrored.get("ttype") is True
        assert mirrored.get("mtts") == mtts
    finally:
        _session_settings.pop(user.pk, None)
