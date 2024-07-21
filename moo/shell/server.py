# -*- coding: utf-8 -*-
"""
AsyncSSH server components.
"""
import os
import asyncio
import logging
import json

from django.contrib.auth.models import User  # pylint: disable=imported-auth-user

from simplesshkey.models import UserKey
import asyncssh
from asyncssh.sftp import SFTPNoSuchFile, SFTPPermissionDenied
from asgiref.sync import sync_to_async
from prompt_toolkit.contrib.ssh import PromptToolkitSSHServer, PromptToolkitSSHSession

from .prompt import embed
from ..core.models import Object, Verb, Property

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
        lambda: SSHServer(interact),
        "",
        port,
        server_host_keys=["/etc/ssh/ssh_host_ecdsa_key"],
        sftp_factory=SFTPServer,
        allow_scp=True
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
            user_pem = ' '.join(user_key.key.split()[:2]) + "\n"
            server_pem = key.export_public_key().decode('utf8')
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

class SFTPServer(asyncssh.SFTPServer):
    """
    Create an SFTP/SCP server for access to Verbs and Properties
    """
    def __init__(self, chan: asyncssh.SSHServerChannel):
        """
        This is initialized in an async context, so we just save
        the username to look up later.
        """
        self.username = username = chan.get_extra_info('username')
        self.user = None
        self.caller = None
        root = '/tmp/moo/' + username
        os.makedirs(root, exist_ok=True)
        super().__init__(chan, chroot=root)

    @sync_to_async
    def download_path(self, path):
        """
        Pre-cache a directory before browsing to it or opening files.
        """
        self.user = User.objects.get(username=self.username)
        self.caller = Object.objects.get(pk=self.user.player.avatar.pk)
        parts = path.decode('utf8').strip('/').split('/')
        obj = None
        if len(parts):
            try:
                obj = Object.objects.get(pk=int(parts[0]))
                self.caller.is_allowed('read', obj, fatal=True)
            except (ValueError, Object.DoesNotExist) as e:
                raise SFTPNoSuchFile(path) from e
            except PermissionError as e:
                raise SFTPPermissionDenied(path) from e
            prefix = os.path.join(self._chroot.decode('utf8'), parts[0])
            os.makedirs(os.path.join(prefix, 'verbs'), exist_ok=True)
            os.makedirs(os.path.join(prefix, 'properties'), exist_ok=True)
        if len(parts) > 1:
            if parts[1] == 'verbs':
                for v in obj.verbs.all():
                    content_path = os.path.join(prefix, 'verbs', v.name() + '.py')
                    if not self.caller.is_allowed('read', v):
                        continue
                    with open(content_path, 'w', encoding='utf8') as f:
                        f.write(v.code)
            elif parts[1] == 'properties':
                for p in obj.properties.all():
                    content_path = os.path.join(prefix, 'properties', p.name + '.json')
                    if not self.caller.is_allowed('read', p):
                        continue
                    with open(content_path, 'w', encoding='utf8') as f:
                        f.write(json.dumps(p.value))

    @sync_to_async
    def upload_path(self, path):
        """
        Given the path of a modified file, upload it appropriately.
        """
        self.user = User.objects.get(username=self.username)
        self.caller = Object.objects.get(pk=self.user.player.avatar.pk)
        path = path[len(self._chroot):]
        parts = path.decode('utf8').strip('/').split('/')
        if len(parts) == 3:
            try:
                obj = Object.objects.get(pk=int(parts[0]))
            except (ValueError, Object.DoesNotExist) as e:
                raise SFTPNoSuchFile(path) from e
            try:
                file_name, _ = parts[2].split('.')
                prefix = os.path.join(self._chroot.decode('utf8'), parts[0])
                if parts[1] == 'verbs':
                    self.caller.is_allowed('develop', obj, fatal=True)
                    v = Verb.objects.get(names__name=file_name, origin=obj)
                    if not self.caller.is_allowed('write', v):
                        raise SFTPPermissionDenied(path)
                    content_path = os.path.join(prefix, 'verbs', v.name() + '.py')
                    with open(content_path, 'r', encoding='utf8') as f:
                        v.code = f.read()
                        v.save()
                elif parts[1] == 'properties':
                    self.caller.is_allowed('write', obj, fatal=True)
                    p = Property.objects.get(name=file_name, origin=obj)
                    if not self.caller.is_allowed('write', p):
                        raise SFTPPermissionDenied(path)
                    content_path = os.path.join(prefix, 'properties', p.name + '.json')
                    with open(content_path, 'r', encoding='utf8') as f:
                        p.value = f.read()
                        p.save()
            except PermissionError as e:
                raise SFTPPermissionDenied(path) from e

    async def open(self, path, *args, **kwargs):  # pylint: disable=invalid-overridden-method
        await self.download_path(path)
        return super().open(path, *args, **kwargs)

    async def open56(self, path, *args, **kwargs):  # pylint: disable=invalid-overridden-method
        await self.download_path(path)
        return super().open56(path, *args, **kwargs)

    async def lstat(self, path):  # pylint: disable=invalid-overridden-method
        await self.download_path(path)
        return super().lstat(path)

    async def close(self, file_obj):  # pylint: disable=invalid-overridden-method
        super().close(file_obj)
        await self.upload_path(file_obj.name)
