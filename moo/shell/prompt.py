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
from prompt_toolkit.application.current import get_app
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console

from ..celery import app
from ..core import code, models, moojson, tasks

log = logging.getLogger(__name__)

# Session-specific output settings registry
# Keyed by user_pk, stores {output_prefix, output_suffix, quiet_mode, color_system}
# Settings are cleared when user disconnects
_session_settings = {}

PROMPT_SHORTCUTS = {
    '"': 'say "%"',
    "'": "say '%'",
}


def _make_key_bindings(automation: bool = False) -> KeyBindings:
    kb = KeyBindings()
    if automation:
        return kb
    buffer_is_empty = Condition(lambda: get_app().current_buffer.text == "")
    for char, template in PROMPT_SHORTCUTS.items():

        def make_handler(ch, tmpl):
            @kb.add(ch, filter=buffer_is_empty)
            def handler(event):
                text = tmpl.replace("%", "")
                pos = tmpl.find("%")
                if pos == -1:
                    pos = len(text)
                event.app.current_buffer.set_document(Document(text, pos))

        make_handler(char, template)
    return kb


async def embed(
    user: models.User,
    automation: bool = False,
) -> None:
    """
    Start the interactive MOO shell for the given user.

    Creates a MooPrompt instance and runs the command and message processing
    coroutines concurrently until either exits.

    :param user: the authenticated Django user whose avatar will be the active player
    :param automation: if True, disables interactive shortcuts (e.g. ``"`` → say)
    """
    repl = MooPrompt(user, automation=automation)
    await asyncio.wait([asyncio.ensure_future(f()) for f in (repl.process_commands, repl.process_messages)])


class MooPrompt:
    """
    Interactive prompt session for a connected MOO user.

    Manages two concurrent async loops: one that reads user input and dispatches
    commands, and one that polls the message queue and prints output sent to the
    user from the MOO world. Editor and paginator requests are routed through
    dedicated asyncio queues so they can interrupt the input prompt cleanly.
    """

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

    def __init__(self, user, automation: bool = False):
        """
        Initialize the prompt session for the given Django user.

        :param user: the authenticated Django user whose avatar will be the active player
        :param automation: if True, disables interactive shortcuts
        """
        self.user = user
        self.automation = automation
        self.is_exiting = False
        self.editor_queue = asyncio.Queue()
        self.paginator_queue = asyncio.Queue()
        self.disconnect_event = asyncio.Event()
        self.last_property_write: datetime | None = None

        # Connection-level output configuration (session-only, not persisted)
        self.output_prefix = None  # Set by PREFIX verb
        self.output_suffix = None  # Set by SUFFIX verb
        self.quiet_mode = False  # Set by QUIET verb
        self.color_system = "truecolor"  # Default: full color support

    async def process_commands(self):
        """
        Read and dispatch user input in a loop.

        Waits simultaneously for a typed command, an editor request, or a
        paginator request. Whichever arrives first is handled; the others are
        cancelled. Exits cleanly on EOF or KeyboardInterrupt.
        """
        prompt_session = PromptSession(key_bindings=_make_key_bindings(self.automation))
        try:
            while not self.is_exiting:
                message = await self.generate_prompt()
                prompt_task = asyncio.ensure_future(prompt_session.prompt_async(message, style=self.style))
                editor_task = asyncio.ensure_future(self.editor_queue.get())
                paginator_task = asyncio.ensure_future(self.paginator_queue.get())
                disconnect_task = asyncio.ensure_future(self.disconnect_event.wait())
                done, pending = await asyncio.wait(
                    [prompt_task, editor_task, paginator_task, disconnect_task], return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                if disconnect_task in done:
                    self.is_exiting = True
                    break
                elif editor_task in done:
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
        finally:
            # Clean up session settings on disconnect
            user_pk = self.user.pk
            if user_pk in _session_settings:
                del _session_settings[user_pk]
                log.debug(f"Cleared session settings for user {user_pk}")
        log.debug("REPL is exiting, stopping main thread...")

    async def run_editor_session(self, req: dict):
        """
        Open the full-screen editor for the given request dict.

        After the user saves or cancels, invokes the callback verb (if
        specified) with the edited text so the MOO world receives the result.

        :param req: editor request dict with keys ``content``, ``content_type``,
            ``callback_this_id``, ``callback_verb_name``, ``caller_id``,
            ``player_id``, and optional ``args``
        """
        from .editor import run_editor

        edited_text = await run_editor(req.get("content", ""), req.get("content_type", "text"), title=req.get("title"))
        if edited_text is not None and req.get("callback_this_id") and req.get("callback_verb_name"):
            caller = await sync_to_async(models.Object.objects.get)(pk=req["caller_id"])
            if not await sync_to_async(caller.is_wizard)():
                log.warning("run_editor_session: rejected callback with non-wizard caller_id=%s", req["caller_id"])
                return
            tasks.invoke_verb.delay(
                edited_text,
                *req.get("args", []),
                caller_id=req["caller_id"],
                player_id=req["player_id"],
                this_id=req["callback_this_id"],
                verb_name=req["callback_verb_name"],
            )

    async def run_paginator_session(self, req: dict):
        """
        Display the given content in the full-screen paginator.

        :param req: paginator request dict with keys ``content`` and ``content_type``
        """
        from .paginator import run_paginator

        await run_paginator(req.get("content", ""), req.get("content_type", "text"))

    @sync_to_async
    def generate_prompt(self):
        """
        Build the prompt_toolkit message tuple for the current location.

        In quiet mode, returns a minimal prompt so automation clients get
        clean output without location noise.

        :returns: list of ``(style_class, text)`` pairs showing the avatar's name
            and current location, e.g. ``Wizard@The Void:$ ``
        """
        settings = _session_settings.get(self.user.pk, {})
        if settings.get("quiet_mode", False):
            return [("", "$ ")]
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

        Updates ``last_connected_time`` on the avatar at most once every 15 seconds
        to avoid excessive property writes. Any exception from the Celery task is
        caught and rendered as a red traceback in the terminal.

        Emits PREFIX and SUFFIX markers if set by the user for machine-readable output.

        :param line: raw input string typed by the user
        """
        caller = self.user.player.avatar
        now = datetime.now(timezone.utc)
        if self.last_property_write is None or (now - self.last_property_write).total_seconds() > 15:
            with code.ContextManager(caller, lambda x: None):
                caller.set_property("last_connected_time", now)
            self.last_property_write = now
        log.info(f"{caller}: {line}")

        # Get session settings for this user
        user_pk = self.user.pk
        settings = _session_settings.get(user_pk, {})
        output_prefix = settings.get("output_prefix")
        output_suffix = settings.get("output_suffix")

        ct = tasks.parse_command.delay(caller.pk, line)
        try:
            output = ct.get()
            if output_prefix:
                self.writer(output_prefix)
            for item in output:
                self.writer(item)
        except:  # pylint: disable=bare-except
            import traceback

            self.writer(f"[bold red]{traceback.format_exc()}[/bold red]")
        finally:
            if output_suffix:
                self.writer(output_suffix)

    def writer(self, s, is_error=False):
        """
        Render a Rich markup string to the terminal via prompt_toolkit.

        Captures Rich's ANSI output and passes it through print_formatted_text
        so it prints above the active input prompt without clobbering it.

        In quiet mode, colors are disabled at the Rich level so no ANSI escape
        sequences are emitted — automation clients receive clean plain text.

        :param s: Rich markup string to render
        :param is_error: reserved for future use; currently unused
        """
        settings = _session_settings.get(self.user.pk, {})
        color_system = None if settings.get("quiet_mode", False) else "truecolor"
        console = Console(color_system=color_system)
        with console.capture() as capture:
            console.print(s)
        content = capture.get()
        print_formatted_text(ANSI(content))

    async def process_messages(self) -> None:
        """
        Poll the Kombu message queue and display incoming MOO output.

        Runs in a loop alongside process_commands. Messages that carry an
        ``editor`` or ``paginator`` event are forwarded to the appropriate
        asyncio queue; all other messages are printed via writer().
        """
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
                        msg = None
                    finally:
                        sb.close()

                    if msg is None:
                        await asyncio.sleep(0.05)
                        continue

                    content = moojson.loads(msg.body)
                    message = content["message"]
                    if isinstance(message, dict) and message.get("event") == "editor":
                        await self.editor_queue.put(message)
                    elif isinstance(message, dict) and message.get("event") == "paginator":
                        await self.paginator_queue.put(message)
                    elif isinstance(message, dict) and message.get("event") == "session_setting":
                        user_pk = self.user.pk
                        if user_pk not in _session_settings:
                            _session_settings[user_pk] = {}
                        _session_settings[user_pk][message["key"]] = message["value"]
                    elif isinstance(message, dict) and message.get("event") == "disconnect":
                        self.is_exiting = True
                        self.disconnect_event.set()
                    else:
                        await run_in_terminal(lambda: self.writer(message))
        except:  # pylint: disable=bare-except
            log.exception("Stopping message processing")
        log.debug("REPL is exiting, stopping messages thread...")
