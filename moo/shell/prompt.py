import asyncio
import logging
import pickle
from asgiref.sync import sync_to_async

from prompt_toolkit import ANSI
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.shortcuts.prompt import PromptSession
from rich.console import Console
from kombu import simple, Exchange, Queue

from ..core import models, tasks
from ..celery import app

log = logging.getLogger(__name__)

async def embed(
    user: models.User,
) -> None:
    repl = MooPrompt(user)
    await asyncio.wait([asyncio.ensure_future(f()) for f in (
        repl.run_async,
        repl.process_messages
    )])

class MooPrompt:
    def __init__(self, user, *a, **kw):
        self.user = user
        self.is_exiting = False

    async def run_async(self):
        prompt_session = PromptSession()
        try:
            while not self.is_exiting:
                if self.is_exiting:
                    log.debug("REPL is exiting, stopping messages thread...")
                    break
                line = await prompt_session.prompt_async("==> ")
                await self.prompt_mud(line)
        except KeyboardInterrupt:
            self.is_exiting = True
        finally:
            pass

    @sync_to_async
    def prompt_mud(self, line: str) -> object:
        """
        Parse the command and execute it.
        """
        caller = self.user.player.avatar
        log.info(f"{caller}: {line}")
        ct = tasks.parse_command.delay(caller.pk, line)
        output = ct.get()
        for item in output:
            self.writer(item)

    def writer(self, s, is_error=False):
        console = Console(color_system="truecolor")
        with console.capture() as capture:
            console.print(s)
        content = capture.get()
        print_formatted_text(ANSI(content))

    async def process_messages(self) -> None:
        await asyncio.sleep(1)
        log.debug(f"Scanning for messages for {self.user}")
        with app.default_connection() as conn:
            channel = conn.channel()
            queue = Queue('messages', Exchange('moo', type='direct', channel=channel), f'user-{self.user.pk}', channel=channel)
            while not self.is_exiting:
                if self.is_exiting:
                    log.debug("REPL is exiting, stopping messages thread...")
                    break
                sb = simple.SimpleBuffer(channel, queue, no_ack=True)
                try:
                    msg = sb.get_nowait()
                except sb.Empty:
                    await asyncio.sleep(1)
                    continue
                if msg:
                    content = pickle.loads(msg.body)
                    await run_in_terminal(lambda: self.writer(content['message']))
                sb.close()
