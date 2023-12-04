import asyncio
import logging

from django.contrib.auth.models import User

import asyncssh
from asgiref.sync import sync_to_async
from prompt_toolkit.contrib.ssh import PromptToolkitSSHServer, PromptToolkitSSHSession

log = logging.getLogger(__name__)

async def interact(ssh_session: PromptToolkitSSHSession) -> None:
    from ptpython.repl import embed
    await embed(return_asyncio_coroutine=True)
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
        return user.check_password(password)
