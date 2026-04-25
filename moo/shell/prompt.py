# -*- coding: utf-8 -*-
"""
Prompt-Toolkit interface for the interactive MOO shell.

See :doc:`/explanation/shell-internals` for the architecture overview —
modes, Kombu message bus, OSC 133 handling, event queues, and teardown.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from asgiref.sync import sync_to_async
from kombu import Exchange, Queue, simple
from prompt_toolkit import ANSI
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.application.current import get_app
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import ThreadedHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console

from ..celery import app
from ..core import code, models, moojson, tasks
from .history import RedisHistory
from .osc import (
    OSC_133_COMMAND_START,
    OSC_133_OUTPUT_START,
    OSC_133_PROMPT_START,
    osc_133_command_end,
)

log = logging.getLogger(__name__)

# Process-local per-session settings, keyed by Django user PK. Cleared on disconnect.
_session_settings: dict[int, dict] = {}

MODE_RICH = "rich"
MODE_RAW = "raw"

PROMPT_SHORTCUTS = {
    '"': 'say "%"',
    "'": "say '%'",
    ":": 'emote "%"',
    ";": '@eval "%"',
}


class _RawAnsi(str):
    """Marker subclass: ``writer`` emits these verbatim, bypassing Rich."""


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
    session=None,
    mode: str = MODE_RICH,
    automation: bool = False,
) -> None:
    """
    Start the interactive MOO shell for the given user.

    Runs ``process_commands`` and ``process_messages`` concurrently and
    tears both down together — see :doc:`/explanation/shell-internals` for
    the teardown rationale.

    :param user: the authenticated Django user whose avatar is the active player
    :param session: the asyncssh session; its ``_chan`` drives raw-mode I/O
    :param mode: ``"rich"`` (default) or ``"raw"``
    :param automation: disables interactive shortcuts; always paired with rich mode
    """
    repl = MooPrompt(user, session=session, mode=mode, automation=automation)
    repl_tasks = [asyncio.ensure_future(f()) for f in (repl.process_commands, repl.process_messages)]
    try:
        await asyncio.wait(repl_tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        repl.is_exiting = True
        repl.disconnect_event.set()
        for task in repl_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*repl_tasks, return_exceptions=True)
        # Safety close in case a task was cancelled before _repl_teardown ran.
        await repl._close_session_buffer()  # pylint: disable=protected-access


class MooPrompt:
    """
    Interactive prompt session for a connected MOO user.

    Runs two concurrent coroutines — ``process_commands`` (input loop) and
    ``process_messages`` (Kombu consumer) — that communicate through
    ``asyncio.Queue`` instances and a few ``asyncio.Event`` flags. See
    :doc:`/explanation/shell-internals` for the full architecture.
    """

    # Shared palette for both prompt_toolkit (rich mode) and Rich (raw mode),
    # so the two modes render the same colours.
    _PROMPT_PALETTE = {
        "": "#ffffff",
        "name": "#884444",
        "at": "#00aa00",
        "colon": "#0000aa",
        "pound": "#00aa00",
        "location": "#00aa55",
    }

    style = Style.from_dict(_PROMPT_PALETTE)

    def __init__(self, user, session=None, mode: str = MODE_RICH, automation: bool = False):
        """
        :param user: the authenticated Django user whose avatar is the active player
        :param session: the asyncssh session; used by raw mode to reach ``_chan``
        :param mode: ``"rich"`` (prompt_toolkit) or ``"raw"`` (line I/O)
        :param automation: if True, disables interactive shortcuts
        """
        self.user = user
        self.mode = mode
        self._chan = getattr(session, "_chan", None) if session is not None else None
        self.automation = automation
        self.is_exiting = False
        # Stamp settings pre-_repl_setup so unit tests that construct a
        # MooPrompt without running the REPL can observe the mode.
        _session_settings.setdefault(self.user.pk, {})["mode"] = mode
        if automation:
            _session_settings[self.user.pk]["automation"] = True
        self.editor_queue: asyncio.Queue = asyncio.Queue()
        self.paginator_queue: asyncio.Queue = asyncio.Queue()
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.disconnect_event = asyncio.Event()
        # Set by _repl_setup once confunc has been published and drained.
        self.startup_drain_complete = asyncio.Event()
        # Set when run_in_terminal is safe to call (rich: first render; raw: immediately).
        self.prompt_app_ready = asyncio.Event()
        # One-entry list so _run_in_terminal_marked can mutate from a closure.
        # True = next render should emit OSC 133 ;A/;B (new prompt anchor).
        self._osc_needs_markers = [True]
        # Rich-rendered ANSI blob of the connect-time confunc burst, flushed
        # via the rich prompt's pre_run callback or raw mode's _chan_write.
        self._pending_connect_output: str = ""
        # Kombu session buffer — one consumer for the whole session. See
        # :doc:`/explanation/shell-internals` § "Single-consumer invariant".
        self._session_conn: Any = None
        self._session_channel: Any = None
        self._session_buffer: Any = None
        self.last_property_write: datetime | None = None

        self.output_prefix = None
        self.output_suffix = None
        self.quiet_mode = False
        self.color_system = "truecolor"

        self._raw_line_buffer: str = ""

    def _osc133_enabled(self) -> bool:
        return _session_settings.get(self.user.pk, {}).get("osc133_mode", True)

    def _prefixes_enabled(self) -> bool:
        return _session_settings.get(self.user.pk, {}).get("prefixes_mode", False)

    def _make_osc_pre_run(self, prompt_session):
        """
        Build a ``pre_run`` callback that flushes the confunc burst and wires
        OSC 133 ;A/;B emission into the prompt's render events — see
        :doc:`/explanation/shell-internals` § "OSC 133 Semantic Shell Integration".
        """

        def pre_run():
            pending = self._pending_connect_output
            if pending:
                self._pending_connect_output = ""
                try:
                    prompt_session.app.output.write_raw(pending)
                    prompt_session.app.output.flush()
                except Exception:  # pylint: disable=broad-except
                    log.exception("failed to flush pending connect-time output")

            def before_render(pt_app):
                if not self._osc_needs_markers[0]:
                    return
                try:
                    pt_app.output.write_raw(OSC_133_PROMPT_START)
                except Exception:  # pylint: disable=broad-except
                    pass

            def after_render(pt_app):
                if not self._osc_needs_markers[0]:
                    return
                try:
                    pt_app.output.write_raw(OSC_133_COMMAND_START)
                    pt_app.output.flush()
                    self._emit_prompt_end_marker()
                    self._osc_needs_markers[0] = False
                except Exception:  # pylint: disable=broad-except
                    pass

            prompt_session.app.before_render += before_render
            prompt_session.app.after_render += after_render
            self.prompt_app_ready.set()

        return pre_run

    async def _run_in_terminal_marked(self, fn):
        """Run ``fn`` via ``run_in_terminal`` and force a fresh OSC 133 anchor."""
        try:
            return await run_in_terminal(fn)
        finally:
            self._osc_needs_markers[0] = True

    async def process_commands(self):
        """Dispatch to the rich or raw command loop based on ``self.mode``."""
        if self.mode == MODE_RAW:
            await self.process_commands_raw()
        else:
            await self.process_commands_rich()

    async def _repl_setup(self) -> None:
        """
        Shared REPL startup: clear stale session state, open the Kombu
        consumer, fire confunc, and coalesce the connect-time output burst
        into ``_pending_connect_output`` — see
        :doc:`/explanation/shell-internals` § "Startup Choreography".
        """
        from django.core.cache import cache

        _session_settings.pop(self.user.pk, None)
        _session_settings.setdefault(self.user.pk, {})["mode"] = self.mode
        if self.automation:
            _session_settings[self.user.pk]["automation"] = True
        cache.set(f"moo:session:{self.user.pk}:mode", self.mode, timeout=86400)
        await self._mark_connected()
        await self._open_session_buffer()
        confunc_tasks = await self._fire_confunc()
        await self._await_tasks(confunc_tasks)
        # Coalesce: Redis round-trip latency can split one tell() burst
        # across multiple reads. Poll until the buffer is empty for three
        # consecutive passes (or we hit the 2s deadline).
        empty_in_a_row = 0
        deadline = asyncio.get_event_loop().time() + 2.0
        pieces: list[str] = []
        while empty_in_a_row < 3 and asyncio.get_event_loop().time() < deadline:
            to_write, events = await self._drain_session_buffer()
            for message in events:
                if message.get("event") == "disconnect":
                    self.is_exiting = True
                    self.disconnect_event.set()
                else:
                    await self._route_event(message)
            if to_write or events:
                empty_in_a_row = 0
                pieces.extend(to_write)
            else:
                empty_in_a_row += 1
            await asyncio.sleep(0.05)
        if pieces:
            settings = _session_settings.get(self.user.pk, {})
            color_system = None if settings.get("quiet_mode", False) else "truecolor"
            console = Console(color_system=color_system, force_terminal=True)
            with console.capture() as capture:
                for piece in pieces:
                    if not isinstance(piece, str):
                        piece = str(piece)
                    console.print(piece, end="\n")
            self._pending_connect_output = capture.get()
        self.startup_drain_complete.set()

    async def _repl_teardown(self) -> None:
        """Shared REPL shutdown: fire disfunc, release session state and the Kombu consumer."""
        from django.core.cache import cache

        self.is_exiting = True
        self.disconnect_event.set()
        await self._fire_disfunc()
        await self._mark_disconnected()
        user_pk = self.user.pk
        if user_pk in _session_settings:
            del _session_settings[user_pk]
            log.debug(f"Cleared session settings for user {user_pk}")
        for key in (
            "mode",
            "quiet_mode",
            "output_prefix",
            "output_suffix",
            "output_global_prefix",
            "output_global_suffix",
            "color_system",
        ):
            cache.delete(f"moo:session:{user_pk}:{key}")
        await self._close_session_buffer()

    async def process_commands_rich(self):
        """
        Rich-mode REPL loop driven by prompt_toolkit.

        Races the user-input prompt against the editor / paginator / input /
        disconnect queues and dispatches whichever fires first.
        """
        prompt_session = PromptSession(
            key_bindings=_make_key_bindings(self.automation),
            history=ThreadedHistory(RedisHistory(self.user.pk)),
        )
        await self._repl_setup()
        try:
            while not self.is_exiting:
                try:
                    from django.core.cache import cache as _cache

                    cols = get_app().output.get_size().columns
                    if _session_settings.get(self.user.pk, {}).get("terminal_width") != cols:
                        _session_settings.setdefault(self.user.pk, {})["terminal_width"] = cols
                        _cache.set(f"moo:session:{self.user.pk}:terminal_width", cols, timeout=86400)
                except Exception:  # pylint: disable=broad-except
                    pass
                message = await self.generate_prompt()
                pre_run = None
                if self._osc133_enabled():
                    pre_run = self._make_osc_pre_run(prompt_session)
                prompt_task = asyncio.ensure_future(
                    prompt_session.prompt_async(message, style=self.style, pre_run=pre_run)
                )
                editor_task = asyncio.ensure_future(self.editor_queue.get())
                paginator_task = asyncio.ensure_future(self.paginator_queue.get())
                input_task = asyncio.ensure_future(self.input_queue.get())
                disconnect_task = asyncio.ensure_future(self.disconnect_event.wait())
                done, pending = await asyncio.wait(
                    [prompt_task, editor_task, paginator_task, input_task, disconnect_task],
                    return_when=asyncio.FIRST_COMPLETED,
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
                        # Editor TUI would hang on keystrokes that never arrive
                        # and break the run_in_terminal Future chain for the rest
                        # of the session.
                        error_pieces = self._editor_rejection_pieces()

                        def _write_editor_error(pieces=error_pieces):  # pylint: disable=dangerous-default-value
                            for piece in pieces:
                                self.writer(piece)

                        await self._run_in_terminal_marked(_write_editor_error)
                    else:
                        await self.run_editor_session(editor_task.result())
                elif paginator_task in done:
                    await self.run_paginator_session(paginator_task.result())
                elif input_task in done:
                    await self.run_input_session(input_task.result())
                elif prompt_task in done:
                    try:
                        line = prompt_task.result()
                    except (EOFError, KeyboardInterrupt):
                        self.is_exiting = True
                        break
                    if line.strip() == ".flush":
                        drain_pieces = await self._drain_messages()
                        if drain_pieces:
                            if self._osc133_enabled():
                                drain_pieces = [
                                    _RawAnsi(OSC_133_OUTPUT_START),
                                    *drain_pieces,
                                    _RawAnsi(osc_133_command_end(0)),
                                ]

                            def _write_drain(pieces=drain_pieces):
                                for piece in pieces:
                                    self.writer(piece)

                            await self._run_in_terminal_marked(_write_drain)
                    else:
                        output_pieces, events = await self.handle_command(line)
                        if output_pieces:

                            def _write_command_output(pieces=output_pieces):
                                for piece in pieces:
                                    self.writer(piece)

                            await self._run_in_terminal_marked(_write_command_output)
                        await self._dispatch_pending_event(events)
        except:  # pylint: disable=bare-except
            log.exception("Error in command processing")
        finally:
            await self._repl_teardown()
        log.debug("REPL is exiting, stopping main thread...")

    async def process_commands_raw(self):
        """
        Raw-mode REPL loop for traditional MUD clients (``TERM=xterm-256-basic``).

        No prompt_toolkit Application, no cursor manipulation — the prompt is
        written once per turn and async output lands on new lines. Editor
        requests are rejected; paginator output is inlined by ``_route_event``.
        """
        await self._repl_setup()
        if self._pending_connect_output:
            self._chan_write(self._pending_connect_output)
            self._pending_connect_output = ""
        self.prompt_app_ready.set()
        try:
            while not self.is_exiting:
                prompt_tuples = await self.generate_prompt()
                rendered = self._render_prompt_tuples(prompt_tuples)
                if self._osc133_enabled():
                    rendered = OSC_133_PROMPT_START + rendered + OSC_133_COMMAND_START
                self._chan_write(rendered)
                self._emit_prompt_end_marker()
                input_task = asyncio.ensure_future(self._read_line_raw())
                editor_task = asyncio.ensure_future(self.editor_queue.get())
                paginator_task = asyncio.ensure_future(self.paginator_queue.get())
                raw_input_task = asyncio.ensure_future(self.input_queue.get())
                disconnect_task = asyncio.ensure_future(self.disconnect_event.wait())
                done, pending = await asyncio.wait(
                    [input_task, editor_task, paginator_task, raw_input_task, disconnect_task],
                    return_when=asyncio.FIRST_COMPLETED,
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
                    for piece in self._editor_rejection_pieces():
                        self.writer(piece)
                elif paginator_task in done:
                    # Unexpected in raw mode (_route_event inlines paginator output);
                    # fall back to a straight dump so nothing is lost.
                    req = paginator_task.result()
                    log.warning("paginator event reached raw REPL loop; process_messages gate may be out of sync")
                    self.writer(req.get("content", ""))
                elif raw_input_task in done:
                    await self.run_input_session(raw_input_task.result())
                elif input_task in done:
                    try:
                        line = input_task.result()
                    except (EOFError, ConnectionResetError):
                        self.is_exiting = True
                        break
                    if line is None:
                        self.is_exiting = True
                        break
                    if line.strip() == ".flush":
                        drain_pieces = await self._drain_messages()
                        if drain_pieces:
                            if self._osc133_enabled():
                                self.writer(_RawAnsi(OSC_133_OUTPUT_START))
                            for piece in drain_pieces:
                                self.writer(piece)
                            if self._osc133_enabled():
                                self.writer(_RawAnsi(osc_133_command_end(0)))
                    else:
                        output_pieces, events = await self.handle_command(line)
                        for piece in output_pieces:
                            self.writer(piece)
                        await self._dispatch_pending_event(events)
        except:  # pylint: disable=bare-except
            log.exception("Error in raw command processing")
        finally:
            await self._repl_teardown()
        log.debug("Raw REPL is exiting, stopping main thread...")

    def _editor_rejection_pieces(self) -> list[str]:
        """Build the "editor not available" error for automation/raw modes."""
        settings = _session_settings.get(self.user.pk, {})
        gp = settings.get("output_global_prefix")
        gs = settings.get("output_global_suffix")
        prefix = "[ERROR] " if self._prefixes_enabled() else ""
        err = (
            f"[bold red]{prefix}Error: editor not available in this mode. "
            "Use '@edit ... with \"...\"' to set content directly.[/bold red]"
        )
        pieces: list[str] = []
        if gp:
            pieces.append(gp)
        pieces.append(err)
        if gs:
            pieces.append(gs)
        return pieces

    def _render_prompt_tuples(self, tuples: list) -> str:
        """Render ``generate_prompt()`` tuples to ANSI for direct channel write."""
        console = Console(color_system="truecolor", force_terminal=True)
        with console.capture() as capture:
            for style_class, text in tuples:
                key = style_class[len("class:") :] if style_class.startswith("class:") else style_class
                colour = self._PROMPT_PALETTE.get(key)
                console.print(text, end="", style=colour)
        return capture.get()

    def _chan_write(self, text: str) -> None:
        """
        Write to the asyncssh channel with LF→CRLF translation (raw mode only).

        The channel is configured in bytes mode (``encoding=None``) so the
        IAC parser can see 0xFF prefix bytes; we UTF-8 encode here before
        sending.
        """
        if self._chan is None:
            return
        self._chan.write(text.replace("\n", "\r\n").encode("utf-8"))

    def _chan_write_iac(self, data: bytes) -> None:
        """
        Write raw IAC bytes to the asyncssh channel.

        No LF→CRLF translation, no encoding. Used for IAC subnegotiation
        frames emitted via the ``"oob"`` event path.
        """
        if self._chan is None:
            return
        try:
            self._chan.write(data)
        except BrokenPipeError:
            pass

    def _emit_prompt_end_marker(self) -> None:
        """
        Emit ``IAC EOR`` or ``IAC GA`` after a prompt render so MUD clients
        and screen readers can detect the server-to-client turnaround.

        EOR is preferred when the client negotiated it (option 25). Some
        older clients still key off GA; we emit GA when EOR is not
        negotiated and the client or server opted into it.

        No-op for clients that did not negotiate either option — both
        bytes would render as garbage in a plain terminal.
        """
        from .iac import encode_eor, encode_ga  # pylint: disable=import-outside-toplevel

        iac = _session_settings.get(self.user.pk, {}).get("iac", {})
        if iac.get("eor"):
            self._chan_write_iac(encode_eor())
        elif iac.get("ga_or_eor"):
            self._chan_write_iac(encode_ga())

    async def _read_line_raw(self) -> str | None:
        """
        Read one line from the SSH channel in raw mode.

        Buffers plain bytes until CR/LF; drops escape sequences (MUD clients
        do their own line editing). Returns ``None`` on EOF.
        """
        from prompt_toolkit.application.current import get_app_session
        from prompt_toolkit.input import Input
        from prompt_toolkit.keys import Keys

        sess = get_app_session()
        inp: Input = sess.input
        with inp.raw_mode():
            with inp.attach(lambda: None):
                while True:
                    for key_press in inp.read_keys():
                        key = key_press.key
                        data = key_press.data
                        if key in (Keys.ControlM, Keys.ControlJ):
                            line = self._raw_line_buffer
                            self._raw_line_buffer = ""
                            self._chan_write("\r\n")
                            return line
                        if key in (Keys.ControlD,) and not self._raw_line_buffer:
                            return None
                        if key in (Keys.Backspace, Keys.ControlH):
                            if self._raw_line_buffer:
                                self._raw_line_buffer = self._raw_line_buffer[:-1]
                                self._chan_write("\b \b")
                            continue
                        if data and not data.startswith("\x1b"):
                            self._raw_line_buffer += data
                            self._chan_write(data)
                    await asyncio.sleep(0.01)

    async def run_editor_session(self, req: dict):
        """
        Open the full-screen editor and invoke the callback verb with the result.

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

    async def _dispatch_pending_event(self, events: list) -> None:
        """
        Pick up any event the just-completed verb published and dispatch it
        directly to the matching handler, bypassing the ``prompt_async`` race
        so the MOO prompt does not flash between a verb and its continuation.

        :param events: list of event-type strings from ``handle_command``
        """
        if not events:
            return
        queue_map = {
            "input_prompt": (self.input_queue, self.run_input_session),
            "editor": (self.editor_queue, self.run_editor_session),
            "paginator": (self.paginator_queue, self.run_paginator_session),
        }
        for event_type in events:
            if event_type not in queue_map:
                continue
            queue, handler = queue_map[event_type]
            try:
                req = await asyncio.wait_for(queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                log.warning("pending %s event did not arrive within 2s", event_type)
                return
            await handler(req)

    async def run_input_session(self, req: dict):
        """
        Show an inline input prompt and invoke the callback verb with the result.

        After dispatch, polls ``input_queue`` briefly for any follow-up prompt
        from the callback so multi-stage input chains stay in one session.
        Automation mode skips the prompt (arguments go in as verb args).

        :param req: input request dict with keys ``prompt``, ``password``,
            ``callback_this_id``, ``callback_verb_name``, ``caller_id``,
            ``player_id``, and optional ``args``
        """
        while req is not None:
            if self.automation:
                return

            prompt_text = req.get("prompt", "")
            is_password = req.get("password", False)

            session = PromptSession()
            try:
                result = await session.prompt_async(
                    ANSI(prompt_text),
                    is_password=is_password,
                )
            except (EOFError, KeyboardInterrupt):
                return

            if not (req.get("callback_this_id") and req.get("callback_verb_name")):
                return
            caller = await sync_to_async(models.Object.objects.get)(pk=req["caller_id"])
            if not await sync_to_async(caller.is_wizard)():
                log.warning("run_input_session: rejected callback with non-wizard caller_id=%s", req["caller_id"])
                return
            tasks.invoke_verb.delay(
                result,
                *req.get("args", []),
                caller_id=req["caller_id"],
                player_id=req["player_id"],
                this_id=req["callback_this_id"],
                verb_name=req["callback_verb_name"],
            )

            try:
                req = await asyncio.wait_for(self.input_queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                return

    @sync_to_async
    def _mark_connected(self):
        """Set the ``is_connected()`` cache key before confunc fires."""
        from django.core.cache import cache

        cache.set(f"moo:connected:{self.user.pk}", True)

    @sync_to_async
    def _mark_disconnected(self):
        """Clear the ``is_connected()`` cache key after disfunc fires."""
        from django.core.cache import cache

        cache.delete(f"moo:connected:{self.user.pk}")

    @sync_to_async
    def _fire_confunc(self):
        """
        Dispatch ``player.confunc`` then ``player.location.confunc`` as Celery
        tasks. Returns the ``AsyncResult`` list so the caller can wait on them.
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
        """Block on Celery tasks, swallowing failures so a broken confunc cannot block the prompt."""
        for result in task_results:
            try:
                result.get(timeout=10, propagate=False)
            except Exception:  # pylint: disable=broad-except
                log.exception("confunc task failed")

    @sync_to_async
    def _fire_disfunc(self):
        """Dispatch ``player.location.disfunc`` then ``player.disfunc`` as Celery tasks."""
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
        Build the prompt message tuple for the current avatar/location.

        :returns: list of ``(style_class, text)`` pairs. Quiet mode returns a
            bare ``$ `` instead.
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
    def handle_command(self, line: str) -> tuple[list, list]:
        """
        Dispatch ``line`` to the parser and collect its output + published events.

        :param line: raw input string typed by the user
        :returns: ``(to_write, events)`` — Rich markup strings to print, and
            event-type strings (``"input_prompt"``, ``"editor"``, ``"paginator"``)
            the verb published during its Celery task.
        """
        from django.core.cache import cache

        caller = self.user.player.avatar
        now = datetime.now(timezone.utc)
        # Rate-limit last_connected_time writes to avoid hammering the DB.
        if self.last_property_write is None or (now - self.last_property_write).total_seconds() > 15:
            with code.ContextManager(caller, lambda x: None):
                caller.set_property("last_connected_time", now)
            self.last_property_write = now
        log.info(f"{caller}: {line}")

        user_pk = self.user.pk
        settings = _session_settings.get(user_pk, {})
        output_prefix = settings.get("output_prefix")
        output_suffix = settings.get("output_suffix")
        output_global_prefix = settings.get("output_global_prefix")
        output_global_suffix = settings.get("output_global_suffix")

        ct = tasks.parse_command.delay(caller.pk, line)
        content = []
        exit_status = 0
        try:
            output, exit_status = ct.get(timeout=30)
            content.extend(output)
        except:  # pylint: disable=bare-except
            import traceback

            exit_status = 1
            content.append(f"[bold red]{traceback.format_exc()}[/bold red]")
        events_key = f"moo:task_events:{ct.id}"
        events = cache.get(events_key) or []
        cache.delete(events_key)
        # Empty-content delimiter frames leave an unresolved run_in_terminal
        # future and hang process_commands — only wrap real output.
        to_write = []
        if content:
            osc133 = self._osc133_enabled()
            if osc133:
                to_write.append(_RawAnsi(OSC_133_OUTPUT_START))
            if output_global_prefix:
                to_write.append(output_global_prefix)
            if output_prefix:
                to_write.append(output_prefix)
            to_write.extend(content)
            if output_suffix:
                to_write.append(output_suffix)
            if output_global_suffix:
                to_write.append(output_global_suffix)
            if osc133:
                to_write.append(_RawAnsi(osc_133_command_end(exit_status)))
        return to_write, events

    @sync_to_async
    def _open_session_buffer(self):
        """Open the per-session Kombu consumer. See :doc:`/explanation/shell-internals`."""
        conn = app.connection_for_read()
        conn.connect()
        channel = conn.channel()
        queue = Queue(
            f"messages.{self.user.pk}",
            Exchange("moo", type="direct", channel=channel),
            f"user-{self.user.pk}",
            channel=channel,
            auto_delete=True,
        )
        sb = simple.SimpleBuffer(channel, queue, no_ack=True)
        self._session_conn = conn
        self._session_channel = channel
        self._session_buffer = sb

    @sync_to_async
    def _close_session_buffer(self):
        """Release the session-long consumer held by ``_open_session_buffer``."""
        sb = self._session_buffer
        channel = self._session_channel
        conn = self._session_conn
        self._session_buffer = None
        self._session_channel = None
        self._session_conn = None
        if sb is not None:
            try:
                sb.close()
            except Exception:  # pylint: disable=broad-except
                log.exception("Error closing session buffer")
        if channel is not None:
            try:
                channel.close()
            except Exception:  # pylint: disable=broad-except
                log.exception("Error closing session channel")
        if conn is not None:
            try:
                conn.release()
            except Exception:  # pylint: disable=broad-except
                log.exception("Error releasing session connection")

    @sync_to_async
    def _drain_session_buffer(self):
        """
        Drain pending Kombu messages; apply ``session_setting`` events in-place
        and return ``(to_write, other_events)`` for the caller.
        """
        to_write = []
        events = []
        sb = self._session_buffer
        if sb is None:
            return to_write, events
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
            elif isinstance(message, dict):
                events.append(message)
            else:
                to_write.append(message)
        return to_write, events

    async def _drain_messages(self):
        """Drain the session buffer for ``.flush``; route any events alongside the text."""
        to_write, events = await self._drain_session_buffer()
        for message in events:
            await self._route_event(message)
        return to_write

    async def _route_event(self, message):
        """Forward a dict-typed broker event to its matching asyncio queue."""
        kind = message.get("event")
        if kind == "oob":
            payload = message.get("data")
            if isinstance(payload, (bytes, bytearray)):
                self._chan_write_iac(bytes(payload))
            return
        if kind == "editor":
            await self.editor_queue.put(message)
        elif kind == "paginator":
            settings = _session_settings.get(self.user.pk, {})
            is_raw = settings.get("mode") == MODE_RAW
            if settings.get("automation") or is_raw:
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

                if is_raw:
                    _write_paginator()
                else:
                    await self._run_in_terminal_marked(_write_paginator)
            else:
                await self.paginator_queue.put(message)
        elif kind == "input_prompt":
            await self.input_queue.put(message)

    def writer(self, s, is_error=False):
        """
        Render a Rich markup string to the terminal. Quiet mode strips colour;
        ``_RawAnsi`` values bypass Rich so OSC sequences survive intact.

        :param s: Rich markup string, or ``_RawAnsi`` for OSC passthrough
        :param is_error: reserved for future use; currently unused
        """
        is_raw_ansi = isinstance(s, _RawAnsi)
        if not isinstance(s, str):
            s = str(s)
        settings = _session_settings.get(self.user.pk, {})
        mode = settings.get("mode", MODE_RICH)
        if is_raw_ansi:
            # Rich escapes OSC sequences and prompt_toolkit's ANSI parser mangles
            # the `\x1b]` introducer, so route OSC passthrough specially.
            if mode == MODE_RAW:
                if self._chan is not None:
                    self._chan.write(s)
                return
            print_formatted_text(FormattedText([("[ZeroWidthEscape]", s)]), end="")
            return
        color_system = None if settings.get("quiet_mode", False) else "truecolor"
        if mode == MODE_RAW:
            console = Console(color_system=color_system, force_terminal=True)
            with console.capture() as capture:
                console.print(s, end="")
            content = capture.get()
            self._chan_write(content + "\n")
            return
        console = Console(color_system=color_system)
        with console.capture() as capture:
            console.print(s, end="")
        content = capture.get()
        print_formatted_text(ANSI(content))

    async def process_messages(self) -> None:
        """
        Kombu consumer loop running alongside ``process_commands``.

        Drains the shared session buffer, routes ``editor`` / ``paginator`` /
        ``input_prompt`` events to their asyncio queues, and emits plain
        strings through ``writer``. Always signals ``process_commands`` to
        exit on teardown so the two coroutines terminate together. See
        :doc:`/explanation/shell-internals` for the full rationale.
        """
        try:
            await asyncio.wait_for(self.startup_drain_complete.wait(), timeout=8.0)
        except asyncio.TimeoutError:
            log.warning("startup_drain_complete not set after 8s — proceeding anyway")
        try:
            # Rich mode: wait for a live Application. Raw mode sets this immediately.
            await asyncio.wait_for(self.prompt_app_ready.wait(), timeout=8.0)
        except asyncio.TimeoutError:
            log.warning("prompt_app_ready not set after 8s — proceeding anyway")
        try:
            while not self.is_exiting:
                # asyncssh doesn't always surface channel close to prompt_toolkit;
                # without this poll prompt_async hangs on a dead channel.
                if self._chan is not None and self._chan.is_closing():
                    self.is_exiting = True
                    self.disconnect_event.set()
                    break
                to_write, events = await self._drain_session_buffer()
                # Coalesce: one run_in_terminal per tell burst, not per message —
                # avoids prompt-flash between every line.
                if to_write or events:
                    for _ in range(10):
                        await asyncio.sleep(0.02)
                        more_write, more_events = await self._drain_session_buffer()
                        if not more_write and not more_events:
                            break
                        to_write.extend(more_write)
                        events.extend(more_events)
                for message in events:
                    if message.get("event") == "disconnect":
                        self.is_exiting = True
                        self.disconnect_event.set()
                    else:
                        await self._route_event(message)
                if to_write:
                    settings = _session_settings.get(self.user.pk, {})
                    gprefix = settings.get("output_global_prefix")
                    gsuffix = settings.get("output_global_suffix")
                    is_raw = settings.get("mode") == MODE_RAW

                    if is_raw:
                        for piece in to_write:
                            if gprefix:
                                self.writer(gprefix)
                            self.writer(piece)
                            if gsuffix:
                                self.writer(gsuffix)
                    else:
                        # Assemble one Rich-rendered blob, emit via a single
                        # run_in_terminal — per-piece writes re-render the prompt
                        # (and re-emit OSC 133 markers) between every line.
                        color_system = None if settings.get("quiet_mode", False) else "truecolor"
                        console = Console(color_system=color_system)
                        with console.capture() as capture:
                            for piece in to_write:
                                if gprefix:
                                    console.print(gprefix, end="")
                                console.print(piece if isinstance(piece, str) else str(piece))
                                if gsuffix:
                                    console.print(gsuffix, end="")
                        blob = capture.get()

                        def _write_blob(b=blob):
                            print_formatted_text(ANSI(b), end="")

                        await self._run_in_terminal_marked(_write_blob)
                if not to_write and not events:
                    await asyncio.sleep(0.05)
        except:  # pylint: disable=bare-except
            log.exception("Stopping message processing")
        finally:
            # Wake process_commands so it exits too — without this a broker
            # disconnect would leave the SSH channel open as a zombie.
            self.is_exiting = True
            self.disconnect_event.set()
        log.debug("REPL is exiting, stopping messages thread...")
