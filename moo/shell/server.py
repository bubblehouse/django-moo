# -*- coding: utf-8 -*-
"""
AsyncSSH server components.
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
    Custom SSH session that selects a shell mode from the client's TERM.

    ``TERM`` values route to:

    - ``xterm-256-basic`` → ``mode="raw"``: line-based I/O for traditional MUD
      clients that cannot handle cursor manipulation or bracketed paste.
    - containing ``moo-automation`` → ``mode="rich"`` with
      ``is_automation=True``: prompt_toolkit TUI with CPR disabled for
      machine-driven command sequences.
    - anything else → ``mode="rich"``: default prompt_toolkit TUI experience.
    """

    user = None  # set by MooSSHServer.session_requested() before the session starts
    is_automation: bool = False
    mode: str = "rich"

    def session_started(self) -> None:
        """Check terminal type and set mode / CPR before starting interaction."""
        if self._chan:
            term = self._chan.get_terminal_type()
            if term and "moo-automation" in term.lower():
                # Automation clients drive the session deterministically and
                # cannot supply CPR responses — leaving CPR enabled here
                # makes prompt_toolkit stall waiting for a reply that never
                # comes.
                self.enable_cpr = False  # type: ignore[attr-defined]
                self.is_automation = True
                self.mode = "rich"
            elif term and term.strip().lower() == "xterm-256-basic":
                self.mode = "raw"
        super().session_started()


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

    # faulthandler.register dumps ALL Python thread stacks synchronously on signal —
    # works even when the asyncio event loop is blocked. loop.add_signal_handler()
    # does NOT work when the loop is frozen because it requires the loop to be
    # alive to deliver the signal callback.
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
