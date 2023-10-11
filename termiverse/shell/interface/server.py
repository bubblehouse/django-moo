import asyncio
import logging
import crypt

import asyncssh

from prompt_toolkit.contrib.ssh import PromptToolkitSSHServer, PromptToolkitSSHSession
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.shortcuts import print_formatted_text as print

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

log = logging.getLogger(__name__)

async def interact(ssh_session: PromptToolkitSSHSession) -> None:
    prompt_session = PromptSession(
        auto_suggest = AutoSuggestFromHistory(),
        history      = InMemoryHistory()
    )
    while(True):
        try:
            text = await prompt_session.prompt_async("> ")
            print("You typed", text)
        except EOFError as e:
            log.info("User disconnected.")
            break
        except KeyboardInterrupt as e:
            pass

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
