import asyncio
import logging
import crypt

import asyncssh

from prompt_toolkit.contrib.ssh import PromptToolkitSSHServer, PromptToolkitSSHSession

log = logging.getLogger(__name__)

async def interact(ssh_session: PromptToolkitSSHSession) -> None:
    from ptpython.repl import embed
    try:
        await embed(return_asyncio_coroutine=True)
    except EOFError:
        pass
    except KeyboardInterrupt:
        pass
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
    passwords = {
        'guest': '',
        'admin': 'qV2iEadIGV2rw' #secretpw
    }

    def begin_auth(self, username: str) -> bool:
        # If the user's password is the empty string, no auth is required
        return self.passwords.get(username) != ''

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        pw = self.passwords.get(username, '*')
        return crypt.crypt(password, pw) == pw
