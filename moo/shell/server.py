# -*- coding: utf-8 -*-
"""
AsyncSSH server entrypoint.

See :doc:`/explanation/shell-internals` for the reasoning behind
``line_editor=False``, the keepalive settings, and the signal handlers.
"""

import asyncio
import faulthandler
import json
import logging
import os
import signal
import sys
from typing import cast

import asyncssh
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from prompt_toolkit.contrib.ssh import PromptToolkitSSHServer, PromptToolkitSSHSession
from simplesshkey.models import UserKey

from .iac import IacNegotiator, IacParser, is_known_mud_client
from .prompt import embed

log = logging.getLogger(__name__)

_active_sessions: set[str] = set()
_total_connections: int = 0


def _fd_count() -> int:
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        return -1


_MUD_CLIENT_TERM_MARKERS = ("mudlet", "tintin", "mushclient", "blowtorch", "mudrammer", "zmud", "cmud")


def _iac_bytes_to_str(data: bytes) -> str:
    """
    Convert raw IAC bytes to a str the surrogate-escape UTF-8 channel
    can re-emit verbatim. ``\\xff`` becomes ``\\udcff``, etc.
    """
    return data.decode("utf-8", errors="surrogateescape")


def _is_mud_term(term: str | None) -> bool:
    """
    True when the SSH client's ``TERM`` string signals a MUD client.

    Matches the existing ``xterm-256-basic`` raw-mode opt-in plus a small
    allowlist of major MUD-client `TERM` values. Anything else (xterm,
    tmux, screen, ...) gets a plain rich-mode session with no IAC
    negotiation, since IAC bytes render as garbage in regular terminals.
    """
    if not term:
        return False
    lowered = term.strip().lower()
    if lowered == "xterm-256-basic":
        return True
    return any(marker in lowered for marker in _MUD_CLIENT_TERM_MARKERS)


class MooPromptToolkitSSHSession(PromptToolkitSSHSession):
    """
    SSH session that selects a shell mode from the client's ``TERM`` and
    speaks the IAC subnegotiation channel on top of SSH for MUD clients.

    For MUD clients (TERM = ``xterm-256-basic`` or a known MUD-client
    name), the channel switches its UTF-8 error policy to
    ``surrogateescape`` so 0xFF IAC bytes round-trip as ``\\udcff``
    surrogate code points: outbound IAC frames go out by decoding raw
    bytes through surrogateescape (the channel's UTF-8 encoder
    re-emits them as the original bytes), and inbound 0xFF arrives as
    surrogate chars in :meth:`data_received` which we re-encode for
    the IAC parser. The channel stays in str mode the whole time, so
    prompt_toolkit's renderer, CPR detection, and Stdout pipeline work
    unchanged. Vanilla SSH terminals leave the channel in strict UTF-8
    and never see an IAC byte.

    See :doc:`/explanation/shell-internals` § "The Three Modes" for
    the full mapping.
    """

    user = None  # set by MooSSHServer.session_requested() before the session starts
    is_automation: bool = False
    mode: str = "rich"
    iac_enabled: bool = False  # set to True in connection_made when TERM looks like a MUD client

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.iac_parser = IacParser()
        self.iac_negotiator = IacNegotiator(
            on_ttype=self._on_ttype,
            on_gmcp=self._on_gmcp,
            on_mssp_request=self._on_mssp_request,
        )

    def _clear_iac_cache(self) -> None:
        """Remove any cached IAC capability snapshot for this user."""
        if self.user is None:
            return
        try:
            from django.core.cache import cache  # pylint: disable=import-outside-toplevel

            from .prompt import _session_settings  # pylint: disable=import-outside-toplevel

            _session_settings.get(self.user.pk, {}).pop("iac", None)
            cache.delete(f"moo:session:{self.user.pk}:iac")
        except Exception:  # pylint: disable=broad-except
            log.exception("failed to clear stale IAC cache for user=%s", self.user)

    def session_started(self) -> None:
        # All TERM-dependent setup happens here, not in connection_made:
        # asyncssh populates the terminal type from the client's PTY request,
        # which arrives between connection_made and session_started.
        if self._chan:
            term = self._chan.get_terminal_type()
            if term and "moo-automation" in term.lower():
                # Automation clients cannot answer CPR — prompt_toolkit would stall.
                self.enable_cpr = False  # type: ignore[attr-defined]
                self.is_automation = True
                self.mode = "rich"
            elif term and term.strip().lower() == "xterm-256-basic":
                self.mode = "raw"
            self.iac_enabled = _is_mud_term(term)
            if self.iac_enabled:
                # Lenient UTF-8 so 0xFF IAC bytes round-trip as \udcff
                # surrogates; the channel stays in str mode so prompt_toolkit's
                # renderer and CPR detection work unchanged.
                self._chan.set_encoding("utf-8", errors="surrogateescape")
            else:
                # Clear any stale IAC capability cache from a previous
                # MUD-client session — send_gmcp would otherwise return True
                # via _client_supports for the next 24h and try to publish
                # OOB events the current client cannot consume.
                self._clear_iac_cache()
        super().session_started()
        # Initial IAC option offers go out only when we're talking to a real
        # MUD client. Automation clients cannot round-trip IAC; vanilla SSH
        # would render the offer bytes as garbage characters. The channel is
        # in surrogate-escape UTF-8 mode for MUD clients, so we feed it str.
        negotiator = getattr(self, "iac_negotiator", None)
        if self.iac_enabled and negotiator is not None and not self.is_automation and self._chan is not None:
            try:
                self._chan.write(_iac_bytes_to_str(negotiator.initial_offers()))
            except BrokenPipeError:
                pass

    def data_received(self, data, datatype) -> None:  # type: ignore[override]
        # Vanilla SSH clients (no MUD-client TERM) — just forward as-is.
        if not self.iac_enabled:
            if self._input is not None and isinstance(data, str):
                self._input.send_text(data)
            return

        # MUD-client path: data is str with possible \udcXX surrogates from
        # surrogateescape decoding. Re-encode to bytes for IAC parsing.
        if isinstance(data, str):
            data_bytes = data.encode("utf-8", errors="surrogateescape")
        else:
            data_bytes = bytes(data)

        events, residual_bytes = self.iac_parser.feed(data_bytes)
        if events:
            prev_caps = dict(self.iac_negotiator.capabilities)
            for event in events:
                reply = self.iac_negotiator.handle(event)
                if reply and self._chan is not None:
                    try:
                        self._chan.write(_iac_bytes_to_str(reply))
                    except BrokenPipeError:
                        return
            # Mirror to _session_settings + cache whenever any capability flipped,
            # not just when TTYPE finalizes — a client may enable GMCP via DO
            # without ever running the TTYPE dance.
            if self.iac_negotiator.capabilities != prev_caps:
                self._mirror_capabilities()
        if residual_bytes and self._input is not None:
            self._input.send_text(residual_bytes.decode("utf-8", errors="surrogateescape"))

    # --- IAC callbacks ------------------------------------------------------

    def _mirror_capabilities(self) -> None:
        """Copy negotiated IAC capabilities into the per-user session settings and cache."""
        if self.user is None:
            return
        from django.core.cache import cache  # pylint: disable=import-outside-toplevel

        from .prompt import _session_settings  # pylint: disable=import-outside-toplevel

        caps = dict(self.iac_negotiator.capabilities)
        _session_settings.setdefault(self.user.pk, {})["iac"] = caps
        # Mirror to cache so Celery workers (separate process) can see it.
        cache.set(f"moo:session:{self.user.pk}:iac", caps, timeout=86400)

    def _on_ttype(self, client_name: str, mtts: int) -> None:
        # Capability mirroring happens in data_received after handle() runs;
        # this callback only records the MUD-client detection for mode-select
        # logic on the next connection.
        if is_known_mud_client(client_name):
            log.info("MTTS detected MUD client user=%s name=%s mtts=%d", self.user, client_name, mtts)

    def _on_gmcp(self, module: str, data: object) -> None:
        # Inbound GMCP from the client — log for now; verb dispatch is future work.
        log.debug("GMCP recv user=%s module=%s data=%r", self.user, module, data)

    def _on_mssp_request(self) -> dict:
        from django.conf import settings as django_settings  # pylint: disable=import-outside-toplevel
        from moo import __version__  # pylint: disable=import-outside-toplevel

        players_online = str(len(_active_sessions))
        return {
            "NAME": getattr(django_settings, "MOO_NAME", "DjangoMOO"),
            "CODEBASE": "DjangoMOO",
            "VERSION": __version__,
            "PLAYERS": players_online,
            "UPTIME": str(_total_connections),
            "FAMILY": "Custom",
            "GENRE": "None",
            "LANGUAGE": "English",
            "CHARSET": "UTF-8",
            "SSL": "0",
        }


async def interact(ssh_session: PromptToolkitSSHSession) -> None:
    """
    Initial entry point for SSH sessions.

    :param ssh_session: the session being started
    """
    global _total_connections  # pylint: disable=global-statement
    session = cast(MooPromptToolkitSSHSession, ssh_session)
    automation = getattr(session, "is_automation", False)
    mode = getattr(session, "mode", "rich")
    username = session.user.username if session.user else "unknown"
    _active_sessions.add(username)
    _total_connections += 1
    log.info(
        "connect user=%s total=%d active=%d fds=%d mode=%s",
        username,
        _total_connections,
        len(_active_sessions),
        _fd_count(),
        mode,
    )
    try:
        await embed(session.user, session=session, mode=mode, automation=automation)
    finally:
        _active_sessions.discard(username)
        log.info("disconnect user=%s active=%d fds=%d", username, len(_active_sessions), _fd_count())


async def _health_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.write(b"OK\n")
    await writer.drain()
    writer.close()


async def server(port=8022):
    """
    Create an AsyncSSH server on the requested port.

    :param port: the port to run the SSH daemon on.
    """
    await asyncio.sleep(1)

    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    loop.slow_callback_duration = 0.050  # warn on any callback >50ms

    # faulthandler dumps thread stacks synchronously, even when the event loop
    # is blocked — unlike loop.add_signal_handler which needs a live loop.
    faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True, chain=False)

    def _dump_state():
        tasks = asyncio.all_tasks()
        log.critical("SIGUSR2 state dump: sessions=%s tasks=%d fds=%d", _active_sessions, len(tasks), _fd_count())
        for t in tasks:
            log.critical("  TASK: %s", t)

    loop.add_signal_handler(signal.SIGUSR2, _dump_state)

    await asyncio.start_server(_health_handler, "", 8023)
    log.info("Health endpoint listening on port 8023")

    await asyncssh.create_server(
        lambda: SSHServer(interact),
        "",
        port,
        server_host_keys=["/etc/ssh/ssh_host_ecdsa_key"],
        kex_algs=[
            "mlkem768x25519-sha256",
            "sntrup761x25519-sha512@openssh.com",
            "curve25519-sha256",
            "ecdh-sha2-nistp256",
            "diffie-hellman-group14-sha256",
        ],
        line_editor=False,
        keepalive_interval=15,
        keepalive_count_max=3,
    )
    await asyncio.Future()


class SSHServer(PromptToolkitSSHServer):
    """
    Create an SSH server for client access.
    """

    def begin_auth(self, _: str) -> bool:
        """
        Allow user login.
        """
        return True

    def password_auth_supported(self) -> bool:
        """
        Allow password authentication.
        """
        return True

    @sync_to_async
    def validate_password(self, username: str, password: str) -> bool:
        """
        Validate a password login.

        :param username: username of the Django User to login as
        :param password: the password string
        """
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return False
        if user.check_password(password):
            self.user = user  # pylint: disable=attribute-defined-outside-init
            return True
        return False

    def public_key_auth_supported(self) -> bool:
        """
        Allow public key authentication.
        """
        return True

    @sync_to_async
    def validate_public_key(self, username: str, key: asyncssh.SSHKey):
        """
        Validate a public key login.

        :param username: username of the Django User to login as
        :param key: the SSH key
        """
        for user_key in UserKey.objects.filter(user__username=username).select_related("user"):
            user_pem = " ".join(user_key.key.split()[:2]) + "\n"
            server_pem = key.export_public_key().decode("utf8")
            if user_pem == server_pem:
                self.user = user_key.user  # pylint: disable=attribute-defined-outside-init
                return True
        return False

    def session_requested(self) -> PromptToolkitSSHSession:
        """
        Setup a session and associate the Django User object.
        """
        session = MooPromptToolkitSSHSession(self.interact, enable_cpr=self.enable_cpr)
        session.user = self.user
        return session
