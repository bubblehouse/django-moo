# -*- coding: utf-8 -*-
"""
Prompt-Toolkit interface
"""

import asyncio
import logging
import pickle

from asgiref.sync import sync_to_async
from kombu import Exchange, Queue, simple
from prompt_toolkit import ANSI
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console

from ..celery import app
from ..core import models, tasks

log = logging.getLogger(__name__)


async def embed(
    user: models.User,
) -> None:
    repl = MooPrompt(user)
    await asyncio.wait([asyncio.ensure_future(f()) for f in (repl.process_commands, repl.process_messages)])


class MooPrompt:
    style = Style.from_dict(
        {
            # User input (default text).
            "": "#ffffff",
            # Prompt.
            "name": "#884444",
            "at": "#00aa00",
            "colon": "#0000aa",
            "pound": "#00aa00",
            "location": "#00aa55",
        }
    )

    def __init__(self, user, *a, **kw):
        self.user = user
        self.is_exiting = False

    async def process_commands(self):
        prompt_session = PromptSession()
        try:
            while not self.is_exiting:
                message = await self.generate_prompt()
                line = await prompt_session.prompt_async(message, style=self.style)
                await self.handle_command(line)
        except EOFError:
            self.is_exiting = True
        except KeyboardInterrupt:
            self.is_exiting = True
        except:  # pylint: disable=bare-except
            log.exception("Error in command processing")
        log.debug("REPL is exiting, stopping main thread...")

    @sync_to_async
    def generate_prompt(self):
        caller = self.user.player.avatar
        caller.refresh_from_db()
        return [
            ("class:name", str(caller.name)),
            ("class:at", "@"),
            ("class:location", str(caller.location.name)),
            ("class:colon", ":"),
            ("class:pound", "$ "),
        ]

    @sync_to_async
    def handle_command(self, line: str) -> object:
        """
        Parse the command and execute it.
        """
        caller = self.user.player.avatar
        log.info(f"{caller}: {line}")
        ct = tasks.parse_command.delay(caller.pk, line)
        try:
            output = ct.get()
            for item in output:
                self.writer(item)
        except:  # pylint: disable=bare-except
            import traceback

            self.writer(f"[bold red]{traceback.format_exc()}[/bold red]")

    def writer(self, s, is_error=False):
        console = Console(color_system="truecolor")
        with console.capture() as capture:
            console.print(s)
        content = capture.get()
        print_formatted_text(ANSI(content))

    async def process_messages(self) -> None:
        await asyncio.sleep(1)
        try:
            with app.default_connection() as conn:
                channel = conn.channel()
                queue = Queue(
                    "messages", Exchange("moo", type="direct", channel=channel), f"user-{self.user.pk}", channel=channel
                )
                while not self.is_exiting:
                    sb = simple.SimpleBuffer(channel, queue, no_ack=True)
                    try:
                        msg = sb.get_nowait()
                    except sb.Empty:
                        await asyncio.sleep(1)
                        continue
                    if msg:
                        content = pickle.loads(msg.body)
                        await run_in_terminal(lambda: self.writer(content["message"]))
                    sb.close()
        except:  # pylint: disable=bare-except
            log.exception("Stopping message processing")
        log.debug("REPL is exiting, stopping messages thread...")
