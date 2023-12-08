import asyncio
import logging

from django.contrib.auth.models import User

from simplesshkey.models import UserKey
import asyncssh
from asgiref.sync import sync_to_async
from prompt_toolkit.contrib.ssh import PromptToolkitSSHServer, PromptToolkitSSHSession

from ..core import code
from .prompt import embed

log = logging.getLogger(__name__)

async def interact(ssh_session: PromptToolkitSSHSession) -> None:
    await embed()
    log.info("User disconnected.")

async def server(port=8022):
    await asyncssh.create_server(
        lambda: SSHServer(interact),
        "",
        port,
        server_host_keys=["/etc/ssh/ssh_host_ecdsa_key"],
    )
    await asyncio.Future()

class SSHServer(PromptToolkitSSHServer):
    def begin_auth(self, _: str) -> bool:
        return True

    def password_auth_supported(self) -> bool:
        return True

    @sync_to_async
    def validate_password(self, username: str, password: str) -> bool:
        try:
            user = User.objects.get(username=username)
        except Exception as e:
            log.error(e)
            return False
        if user.check_password(password):
            code.set_caller(user)
            return True
        return False

    def public_key_auth_supported(self) -> bool:
        return True

    @sync_to_async
    def validate_public_key(self, username: str, key: asyncssh.SSHKey):
        try:
            for user_key in UserKey.objects.filter(user__username=username):
                user_pem = ' '.join(user_key.key.split()[:2]) + "\n"
                server_pem = key.export_public_key().decode('utf8')
                if user_pem == server_pem:
                    code.set_caller(user_key.user)
                    return True
        except Exception as e:
            log.error(e)
            return False
        return False
