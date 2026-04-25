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


class MooPromptToolkitSSHSession(PromptToolkitSSHSession):
    """
    SSH session that selects a shell mode from the client's ``TERM`` and
    speaks the IAC subnegotiation channel on top of SSH.

    The channel is switched to bytes mode (``encoding=None``) during
    :meth:`connection_made` so the :class:`IacParser` can see 0xFF
    prefix bytes directly. Outbound prompt_toolkit/Rich text is UTF-8
    encoded in :meth:`_encoded_stdout_write` before reaching the channel.

    See :doc:`/explanation/shell-internals` § "The Three Modes" for the
    full mapping.
    """

    user = None  # set by MooSSHServer.session_requested() before the session starts
    is_automation: bool = False
    mode: str = "rich"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.iac_parser = IacParser()
        self.iac_negotiator = IacNegotiator(
            on_ttype=self._on_ttype,
            on_gmcp=self._on_gmcp,
            on_mssp_request=self._on_mssp_request,
        )

    def connection_made(self, chan) -> None:
        super().connection_made(chan)
        # Bytes mode so the IAC parser can see 0xFF prefix bytes. Rich/
        # prompt_toolkit output is UTF-8 encoded in _encoded_stdout_write.
        chan.set_encoding(None)

        def _encoded_stdout_write(data: str) -> None:
            try:
                if self._chan is not None:
                    self._chan.write(data.replace("\n", "\r\n").encode("utf-8"))
            except BrokenPipeError:
                pass

        self.stdout.write = _encoded_stdout_write  # type: ignore[method-assign]

    def session_started(self) -> None:
        if self._chan:
            term = self._chan.get_terminal_type()
            if term and "moo-automation" in term.lower():
                # Automation clients cannot answer CPR — prompt_toolkit would stall.
                self.enable_cpr = False  # type: ignore[attr-defined]
                self.is_automation = True
                self.mode = "rich"
            elif term and term.strip().lower() == "xterm-256-basic":
                self.mode = "raw"
        super().session_started()
        # Send initial IAC option offers on session start. Automation clients
        # cannot round-trip IAC safely, so we suppress negotiation for them.
        negotiator = getattr(self, "iac_negotiator", None)
        if negotiator is not None and not self.is_automation and self._chan is not None:
            try:
                self._chan.write(negotiator.initial_offers())
            except BrokenPipeError:
                pass

    def data_received(self, data, datatype) -> None:  # type: ignore[override]
        # With encoding=None on the channel, asyncssh delivers raw bytes here.
        if not isinstance(data, (bytes, bytearray)):
            # Fallback for automation/tests that still feed str through.
            if self._input is not None:
                self._input.send_text(data)
            return

        events, residual = self.iac_parser.feed(bytes(data))
        if events:
            prev_caps = dict(self.iac_negotiator.capabilities)
            for event in events:
                reply = self.iac_negotiator.handle(event)
                if reply and self._chan is not None:
                    try:
                        self._chan.write(reply)
                    except BrokenPipeError:
                        return
            # Mirror to _session_settings + cache whenever any capability flipped,
            # not just when TTYPE finalizes — a client may enable GMCP via DO
            # without ever running the TTYPE dance.
            if self.iac_negotiator.capabilities != prev_caps:
                self._mirror_capabilities()
        if residual and self._input is not None:
            try:
                text = residual.decode("utf-8")
            except UnicodeDecodeError:
                text = residual.decode("utf-8", errors="replace")
            self._input.send_text(text)

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
