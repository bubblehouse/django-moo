# -*- coding: utf-8 -*-
"""
AsyncSSH server components.
"""
import asyncio
import json
import logging
import os

import asyncssh
from asgiref.sync import sync_to_async
from django.contrib.auth.models import \
    User  # pylint: disable=imported-auth-user
from prompt_toolkit.contrib.ssh import (PromptToolkitSSHServer,
                                        PromptToolkitSSHSession)
from simplesshkey.models import UserKey

from .prompt import embed

log = logging.getLogger(__name__)


async def interact(ssh_session: PromptToolkitSSHSession) -> None:
    """
    Initial entry point for SSH sessions.

    :param ssh_session: the session being started
    """
    await embed(ssh_session.user)
    log.info(f"{ssh_session.user} disconnected.")


async def server(port=8022):
    """
    Create an AsyncSSH server on the requested port.

    :param port: the port to run the SSH daemon on.
    """
    await asyncio.sleep(1)
    await asyncssh.create_server(
        lambda: SSHServer(interact), "", port, server_host_keys=["/etc/ssh/ssh_host_ecdsa_key"]
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
        user = User.objects.get(username=username)
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
        for user_key in UserKey.objects.filter(user__username=username):
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
        session = PromptToolkitSSHSession(self.interact, enable_cpr=self.enable_cpr)
        session.user = self.user
        return session
