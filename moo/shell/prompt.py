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
_session_settings: dict[int, dict] = {}

PROMPT_SHORTCUTS = {
    '"': 'say "%"',
    "'": "say '%'",
    ":": 'emote "%"',
    ";": '@eval "%"',
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
        if automation:
            _session_settings.setdefault(self.user.pk, {})["automation"] = True
        self.editor_queue: asyncio.Queue = asyncio.Queue()
        self.paginator_queue: asyncio.Queue = asyncio.Queue()
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
        # Clear any session settings left over from a previous connection on
        # this account (e.g. an agent that enabled QUIET/OUTPUTPREFIX).
        _session_settings.pop(self.user.pk, None)
        if self.automation:
            _session_settings.setdefault(self.user.pk, {})["automation"] = True
        await self._mark_connected()
        confunc_tasks = await self._fire_confunc()
        await self._await_tasks(confunc_tasks)
        startup_pieces = await self._drain_messages()
        if startup_pieces:

            def _write_startup(pieces=startup_pieces):
                for piece in pieces:
                    self.writer(piece)

            await run_in_terminal(_write_startup)
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
                    if self.automation:
                        # The editor TUI cannot run in automation mode — doing so
                        # hangs app.run_async() waiting for keystrokes that never
                        # arrive, which corrupts the run_in_terminal Future chain
                        # and breaks every subsequent command in the session.
                        # Send a delimited error so the automation client can retry
                        # with `@edit ... with "..."`.
                        settings = _session_settings.get(self.user.pk, {})
                        gp = settings.get("output_global_prefix")
                        gs = settings.get("output_global_suffix")
                        err = (
                            "[bold red]Error: editor not available in automation mode. "
                            "Use '@edit ... with \"...\"' to set content directly.[/bold red]"
                        )
                        error_pieces = []
                        if gp:
                            error_pieces.append(gp)
                        error_pieces.append(err)
                        if gs:
                            error_pieces.append(gs)

                        def _write_editor_error(pieces=error_pieces):  # pylint: disable=dangerous-default-value
                            for piece in pieces:
                                self.writer(piece)

                        await run_in_terminal(_write_editor_error)
                    else:
                        await self.run_editor_session(editor_task.result())
                elif paginator_task in done:
                    await self.run_paginator_session(paginator_task.result())
                elif prompt_task in done:
                    try:
                        line = prompt_task.result()
                    except (EOFError, KeyboardInterrupt):
                        self.is_exiting = True
                        break
                    if line.strip() == ".flush":
                        drain_pieces = await self._drain_messages()
                        if drain_pieces:

                            def _write_drain(pieces=drain_pieces):
                                for piece in pieces:
                                    self.writer(piece)

                            await run_in_terminal(_write_drain)
                    else:
                        output_pieces = await self.handle_command(line)
                        if output_pieces:

                            def _write_command_output(pieces=output_pieces):
                                for piece in pieces:
                                    self.writer(piece)

                            await run_in_terminal(_write_command_output)
        except:  # pylint: disable=bare-except
            log.exception("Error in command processing")
        finally:
            # Signal process_messages to stop regardless of how we exited.
            # Without this, if process_commands exits via exception, is_exiting
            # is never set and process_messages loops forever — keeping the
            # asyncssh channel open as a zombie.
            self.is_exiting = True
            self.disconnect_event.set()
            await self._fire_disfunc()
            await self._mark_disconnected()
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
    def _mark_connected(self):
        """
        Set the Redis cache key that signals this player is connected.

        Called at session start, before confunc fires, so that ``is_connected()``
        returns ``True`` by the time the room's confunc announces the arrival.
        """
        from django.core.cache import cache

        cache.set(f"moo:connected:{self.user.pk}", True)

    @sync_to_async
    def _mark_disconnected(self):
        """
        Remove the Redis cache key that signals this player is connected.

        Called in the finally block after disfunc fires so that ``is_connected()``
        returns ``False`` for any subsequent room broadcasts.
        """
        from django.core.cache import cache

        cache.delete(f"moo:connected:{self.user.pk}")

    @sync_to_async
    def _fire_confunc(self):
        """
        Dispatch confunc verbs on SSH connect.

        Calls ``player.confunc()`` first (personal hooks: mail, news), then
        ``player.location.confunc()`` (room hook: show room, announce arrival).
        Both are dispatched as Celery tasks so they run asynchronously.

        Returns the list of AsyncResult objects so the caller can wait for
        completion before draining the message queue.
        """
        player = self.user.player.avatar
        results = []
        if player.has_verb("confunc"):
            results.append(
                tasks.invoke_verb.delay(
                    caller_id=player.pk,
                    player_id=player.pk,
                    this_id=player.pk,
                    verb_name="confunc",
                )
            )
        if player.location and player.location.has_verb("confunc"):
            results.append(
                tasks.invoke_verb.delay(
                    caller_id=player.pk,
                    player_id=player.pk,
                    this_id=player.location.pk,
                    verb_name="confunc",
                )
            )
        return results

    @sync_to_async
    def _await_tasks(self, task_results):
        """
        Block until all Celery tasks in ``task_results`` have completed.

        Uses the result backend so the caller knows it is safe to drain the
        message queue — any ``print()`` output published by those tasks will
        already be in the queue.  Failures are swallowed so a broken confunc
        verb does not prevent the prompt from appearing.
        """
        for result in task_results:
            try:
                result.get(timeout=10, propagate=False)
            except Exception:  # pylint: disable=broad-except
                log.exception("confunc task failed")

    @sync_to_async
    def _fire_disfunc(self):
        """
        Dispatch disfunc verbs on SSH disconnect.

        Calls ``player.location.disfunc()`` first (room hook: move player home,
        announce departure), then ``player.disfunc()`` (personal cleanup hook).
        Both are dispatched as Celery tasks so they run asynchronously.
        """
        player = self.user.player.avatar
        if player.location and player.location.has_verb("disfunc"):
            tasks.invoke_verb.delay(
                caller_id=player.pk,
                player_id=player.pk,
                this_id=player.location.pk,
                verb_name="disfunc",
            )
        if player.has_verb("disfunc"):
            tasks.invoke_verb.delay(
                caller_id=player.pk,
                player_id=player.pk,
                this_id=player.pk,
                verb_name="disfunc",
            )

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
    def handle_command(self, line: str) -> list:
        """
        Parse the command and execute it.

        Updates ``last_connected_time`` on the avatar at most once every 15 seconds
        to avoid excessive property writes. Any exception from the Celery task is
        caught and rendered as a red traceback in the terminal.

        Returns a list of Rich markup strings to be written by the caller via
        ``run_in_terminal``, so that output is safely delivered from the async
        event loop thread rather than from this sync executor thread.

        :param line: raw input string typed by the user
        :returns: list of Rich markup strings to write to the terminal
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
        output_global_prefix = settings.get("output_global_prefix")
        output_global_suffix = settings.get("output_global_suffix")

        ct = tasks.parse_command.delay(caller.pk, line)
        content = []
        try:
            output = ct.get(timeout=30)
            content.extend(output)
        except:  # pylint: disable=bare-except
            import traceback

            content.append(f"[bold red]{traceback.format_exc()}[/bold red]")
        # Only wrap with prefix/suffix delimiters when there is actual content.
        # Sending empty-content delimiter frames in automation mode leaves an
        # unresolved run_in_terminal future and hangs process_commands.
        to_write = []
        if content:
            if output_global_prefix:
                to_write.append(output_global_prefix)
            if output_prefix:
                to_write.append(output_prefix)
            to_write.extend(content)
            if output_suffix:
                to_write.append(output_suffix)
            if output_global_suffix:
                to_write.append(output_global_suffix)
        return to_write

    @sync_to_async
    def _drain_messages(self):
        """
        Drain all pending Kombu messages and return them for writing.

        This implements the ``.flush`` connection-level command: any async output
        (tell() messages, system notices) that has accumulated in the message queue
        since the last poll cycle is collected here.  Session setting events
        encountered during the drain are applied normally.

        Returns a list of Rich markup strings; the caller writes them via
        ``run_in_terminal`` so they are delivered from the event loop thread.

        Useful for automation clients that want a clean separation between async
        background output and the response to the next command they are about to send.
        """
        to_write = []
        with app.default_connection() as conn:
            channel = conn.channel()
            queue = Queue(
                f"messages.{self.user.pk}",
                Exchange("moo", type="direct", channel=channel),
                f"user-{self.user.pk}",
                channel=channel,
            )
            sb = simple.SimpleBuffer(channel, queue, no_ack=True)
            try:
                while True:
                    try:
                        msg = sb.get_nowait()
                    except sb.Empty:
                        break
                    content = moojson.loads(msg.body)
                    message = content["message"]
                    if isinstance(message, dict) and message.get("event") == "session_setting":
                        user_pk = self.user.pk
                        if user_pk not in _session_settings:
                            _session_settings[user_pk] = {}
                        _session_settings[user_pk][message["key"]] = message["value"]
                    elif not isinstance(message, dict):
                        to_write.append(message)
            finally:
                sb.close()
        return to_write

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
        if not isinstance(s, str):
            s = str(s)
        settings = _session_settings.get(self.user.pk, {})
        color_system = None if settings.get("quiet_mode", False) else "truecolor"
        console = Console(color_system=color_system)
        with console.capture() as capture:
            console.print(s, end="")
        content = capture.get()
        print_formatted_text(ANSI(content))

    async def process_messages(self) -> None:
        """
        Poll the Kombu message queue and display incoming MOO output.

        Runs in a loop alongside process_commands. Messages that carry an
        ``editor`` or ``paginator`` event are forwarded to the appropriate
        asyncio queue; all other messages are printed via writer().

        A single ``SimpleBuffer`` (and its underlying AMQP consumer) is held
        open for the duration of the session.  Previously the buffer was
        created and torn down on every iteration (20×/second per agent), which
        caused excessive consumer churn on the broker and could trigger channel
        errors that silently killed this coroutine while ``process_commands``
        kept the SSH connection open indefinitely as a zombie.

        The ``finally`` block signals ``process_commands`` to exit whenever
        this coroutine ends — whether by normal exit, exception, or
        ``disconnect`` event — so the two tasks always terminate together.
        """
        await asyncio.sleep(1)
        try:
            with app.default_connection() as conn:
                channel = conn.channel()
                queue = Queue(
                    f"messages.{self.user.pk}",
                    Exchange("moo", type="direct", channel=channel),
                    f"user-{self.user.pk}",
                    channel=channel,
                )
                sb = simple.SimpleBuffer(channel, queue, no_ack=True)
                try:
                    while not self.is_exiting:
                        try:
                            msg = sb.get_nowait()
                        except sb.Empty:
                            msg = None

                        if msg is None:
                            await asyncio.sleep(0.05)
                            continue

                        content = moojson.loads(msg.body)
                        message = content["message"]
                        if isinstance(message, dict) and message.get("event") == "editor":
                            await self.editor_queue.put(message)
                        elif isinstance(message, dict) and message.get("event") == "paginator":
                            settings = _session_settings.get(self.user.pk, {})
                            if settings.get("automation"):
                                content = message.get("content", "")

                                def _write_paginator(
                                    msg=content,
                                    gp=settings.get("output_global_prefix"),
                                    gs=settings.get("output_global_suffix"),
                                ):
                                    if gp:
                                        self.writer(gp)
                                    self.writer(msg)
                                    if gs:
                                        self.writer(gs)

                                await run_in_terminal(_write_paginator)
                            else:
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
                            settings = _session_settings.get(self.user.pk, {})
                            gprefix = settings.get("output_global_prefix")
                            gsuffix = settings.get("output_global_suffix")

                            def _write_message(msg=message, gp=gprefix, gs=gsuffix):
                                if gp:
                                    self.writer(gp)
                                self.writer(msg)
                                if gs:
                                    self.writer(gs)

                            await run_in_terminal(_write_message)
                finally:
                    sb.close()
        except:  # pylint: disable=bare-except
            log.exception("Stopping message processing")
        finally:
            # Signal process_commands to exit. If this coroutine crashes
            # (e.g. broker disconnect), process_commands would otherwise spin
            # forever waiting for input, keeping the SSH channel open as a
            # zombie. Setting is_exiting + disconnect_event ensures it wakes
            # up and exits cleanly regardless of how we got here.
            self.is_exiting = True
            self.disconnect_event.set()
        log.debug("REPL is exiting, stopping messages thread...")
