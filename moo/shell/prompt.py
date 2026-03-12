# -*- coding: utf-8 -*-
"""
Prompt-Toolkit interface
"""

import asyncio
import logging
from datetime import datetime, timezone

from asgiref.sync import sync_to_async
from kombu import Exchange, Queue, simple
from prompt_toolkit import ANSI
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console

from ..celery import app
from ..core import code, models, moojson, tasks

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
        self.editor_queue = asyncio.Queue()
        self.paginator_queue = asyncio.Queue()
        self.last_property_write: datetime | None = None

    async def process_commands(self):
        prompt_session = PromptSession()
        try:
            while not self.is_exiting:
                message = await self.generate_prompt()
                prompt_task = asyncio.ensure_future(
                    prompt_session.prompt_async(message, style=self.style))
                editor_task = asyncio.ensure_future(self.editor_queue.get())
                paginator_task = asyncio.ensure_future(self.paginator_queue.get())
                done, pending = await asyncio.wait(
                    [prompt_task, editor_task, paginator_task], return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                if editor_task in done:
                    await self.run_editor_session(editor_task.result())
                elif paginator_task in done:
                    await self.run_paginator_session(paginator_task.result())
                elif prompt_task in done:
                    try:
                        line = prompt_task.result()
                    except (EOFError, KeyboardInterrupt):
                        self.is_exiting = True
                        break
                    await self.handle_command(line)
        except:  # pylint: disable=bare-except
            log.exception("Error in command processing")
        log.debug("REPL is exiting, stopping main thread...")

    async def run_editor_session(self, req: dict):
        from .editor import run_editor
        edited_text = await run_editor(req.get("content", ""), req.get("content_type", "text"))
        if edited_text is not None and req.get("callback_this_id") and req.get("callback_verb_name"):
            tasks.invoke_verb.delay(
                edited_text,
                *req.get("args", []),
                caller_id=req["caller_id"],
                player_id=req["player_id"],
                this_id=req["callback_this_id"],
                verb_name=req["callback_verb_name"],
            )

    async def run_paginator_session(self, req: dict):
        from .paginator import run_paginator
        await run_paginator(req.get("content", ""), req.get("content_type", "text"))

    @sync_to_async
    def generate_prompt(self):
        caller = self.user.player.avatar
        caller.refresh_from_db()
        return [
            ("class:name", str(caller.name)),
            ("class:at", "@"),
            ("class:location", str(caller.location.name) if caller.location else "nowhere"),
            ("class:colon", ":"),
            ("class:pound", "$ "),
        ]

    @sync_to_async
    def handle_command(self, line: str) -> object:
        """
        Parse the command and execute it.
        """
        caller = self.user.player.avatar
        now = datetime.now(timezone.utc)
        if self.last_property_write is None or (now - self.last_property_write).total_seconds() > 15:
            with code.ContextManager(caller, lambda x: None):
                caller.set_property("last_connected_time", now)
            self.last_property_write = now
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
                        content = moojson.loads(msg.body)
                        message = content["message"]
                        if isinstance(message, dict) and message.get("event") == "editor":
                            await self.editor_queue.put(message)
                        elif isinstance(message, dict) and message.get("event") == "paginator":
                            await self.paginator_queue.put(message)
                        else:
                            await run_in_terminal(lambda: self.writer(message))
                    sb.close()
        except:  # pylint: disable=bare-except
            log.exception("Stopping message processing")
        log.debug("REPL is exiting, stopping messages thread...")
