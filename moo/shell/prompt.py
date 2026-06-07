# -*- coding: utf-8 -*-
"""
Prompt-Toolkit interface for the interactive MOO shell.

See :doc:`/explanation/shell-internals` for the architecture overview —
modes, Kombu message bus, OSC 133 handling, event queues, and teardown.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional

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


def _make_key_bindings() -> KeyBindings:
    kb = KeyBindings()
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
    site=None,
) -> None:
    """
    Start the interactive MOO shell for the given user.

    Runs ``process_commands`` and ``process_messages`` concurrently and
    tears both down together — see :doc:`/explanation/shell-internals` for
    the teardown rationale.

    :param user: the authenticated Django user whose avatar is the active player
    :param session: the asyncssh session; its ``_chan`` drives raw-mode I/O
    :param mode: ``"rich"`` (default) or ``"raw"``
    :param site: the Django Site for this connection (used to scope universe context)
    """
    from moo.core.code import ContextManager

    # Stamp the site on this asyncio task's contextvars so direct ORM queries
    # in MooPrompt (Object.objects.get(pk=...) at command-dispatch and
    # editor-completion time) hit the right universe. Each SSH session runs
    # in its own asyncio task with isolated contextvars, so this does not
    # bleed into other sessions. Celery tasks build their own ContextManager
    # with site= derived from caller.site, independent of this stamp.
    if site is not None:
        ContextManager.set_site(site)
    repl = MooPrompt(user, session=session, mode=mode, site=site)
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

    #: prompt-toolkit Style derived from the prompt palette.
    style = Style.from_dict(_PROMPT_PALETTE)

    def __init__(self, user, session=None, mode: str = MODE_RICH, site=None):
        """
        :param user: the authenticated Django user whose avatar is the active player
        :param session: the asyncssh session; used by raw mode to reach ``_chan``
        :param mode: ``"rich"`` (prompt_toolkit) or ``"raw"`` (line I/O)
        :param site: the Django Site for this connection
        """
        self.user = user
        self.mode = mode
        self.site = site
        self._chan = getattr(session, "_chan", None) if session is not None else None
        self._iac_enabled = bool(getattr(session, "iac_enabled", False)) if session is not None else False
        self.is_exiting = False
        # Stamp settings pre-_repl_setup so unit tests that construct a
        # MooPrompt without running the REPL can observe the mode.
        _session_settings.setdefault(self.user.pk, {})["mode"] = mode
        self.editor_queue: asyncio.Queue = asyncio.Queue()
        self.paginator_queue: asyncio.Queue = asyncio.Queue()
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.window_queue: asyncio.Queue = asyncio.Queue()
        # Persistent windowed-display mode (see moo/shell/window.py). When a
        # window is active, process_messages routes output into the running
        # Application's scroll buffer instead of run_in_terminal.
        self._window_app: Any = None
        self._window_state: Any = None
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

    def _get_avatar(self):
        """
        Look up the player avatar for this user on the active site.

        Player.user is a ForeignKey (multi-universe), so a single Django user
        can hold a separate Player per site.  Falls back to the user's only
        Player if no site-scoped record exists, which keeps single-universe
        deployments working when ``site`` is None.
        """
        from moo.core.models.auth import Player

        record = None
        if self.site is not None:
            record = Player.objects.filter(user=self.user, site=self.site).first()
        if record is None:
            record = Player.objects.filter(user=self.user).first()
        return record.avatar if record else None

    def _osc133_enabled(self) -> bool:
        # MUD clients don't speak OSC 133; the BEL-terminated frames upset
        # Mudlet's prompt-line heuristic and swallow the trailing IAC GA.
        if self._iac_enabled:
            return False
        return _session_settings.get(self.user.pk, {}).get("osc133_mode", True)

    def _prefixes_enabled(self) -> bool:
        return _session_settings.get(self.user.pk, {}).get("prefixes_mode", False)

    def _make_pre_run(self, prompt_session, with_osc133):
        """
        Build a ``pre_run`` callback that always flushes the confunc burst
        before the first prompt renders. When ``with_osc133`` is True, also
        wire OSC 133 ;A/;B emission into the prompt's render events — see
        :doc:`/explanation/shell-internals` § "OSC 133 Semantic Shell Integration".

        The flush MUST run even when OSC 133 is disabled (e.g. MUD clients
        connecting via IAC), otherwise the on-connect ``look`` output is
        silently dropped and the user sees the prompt on a blank screen.
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

            if with_osc133:

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
            color_system: Optional[Literal["truecolor"]] = None if settings.get("quiet_mode", False) else "truecolor"
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
        # Exit a live window Application so it restores the terminal cleanly.
        if self._window_app is not None:
            try:
                self._window_app.exit()
            except Exception:  # pylint: disable=broad-except
                pass
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
            "iac",
            "window_active",
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
            key_bindings=_make_key_bindings(),
            history=ThreadedHistory(RedisHistory(self.user.pk)),
        )

        # Fix: log the timeout to the server log (so real failures remain detectable) but
        # never call run_in_terminal(), so no orphaned task is ever created.
        def _safe_cpr_not_supported(app=prompt_session.app):  # pylint: disable=redefined-outer-name
            if app.output.responds_to_cpr:
                log.warning(
                    "CPR query timed out for user=%s — terminal did not respond within 2s",
                    self.user,
                )

        prompt_session.app.cpr_not_supported_callback = _safe_cpr_not_supported
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
                pre_run = self._make_pre_run(prompt_session, with_osc133=self._osc133_enabled())
                prompt_task = asyncio.ensure_future(
                    prompt_session.prompt_async(message, style=self.style, pre_run=pre_run)
                )
                editor_task = asyncio.ensure_future(self.editor_queue.get())
                paginator_task = asyncio.ensure_future(self.paginator_queue.get())
                input_task = asyncio.ensure_future(self.input_queue.get())
                window_task = asyncio.ensure_future(self.window_queue.get())
                disconnect_task = asyncio.ensure_future(self.disconnect_event.wait())
                done, pending = await asyncio.wait(
                    [prompt_task, editor_task, paginator_task, input_task, window_task, disconnect_task],
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
                    await self.run_editor_session(editor_task.result())
                elif paginator_task in done:
                    await self.run_paginator_session(paginator_task.result())
                elif input_task in done:
                    await self.run_input_session(input_task.result())
                elif window_task in done:
                    await self.run_window_session(window_task.result())
                elif prompt_task in done:
                    try:
                        line = prompt_task.result()
                    except (EOFError, KeyboardInterrupt):
                        self.is_exiting = True
                        break
                    if not line.strip():
                        # Silently swallow empty lines. Some MUD clients
                        # (Mudlet without "Strict UNIX line endings", etc.)
                        # send a stray LF after each CR-LF terminated command;
                        # we don't want those to redraw a "what now?" prompt.
                        continue
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
                    if not line.strip():
                        # See note above: empty lines from CR-LF clients are dropped.
                        continue
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
                        # Async tell() output (e.g. exit.move's leave/arrive
                        # broadcasts) lands in Kombu, not in handle_command's
                        # return value. Drain it here so it appears before the
                        # next prompt instead of below it.
                        await self._drain_async_tell_output()
        except asyncio.CancelledError:
            # Unclean SSH disconnect — asyncio.wait() inside the REPL loop
            # gets cancelled when the channel goes away.  Log compactly
            # rather than dumping a stack trace.
            log.info("Raw REPL cancelled (client disconnected).")
        except:  # pylint: disable=bare-except
            log.exception("Error in raw command processing")
        finally:
            await self._repl_teardown()
        log.debug("Raw REPL is exiting, stopping main thread...")

    async def _drain_async_tell_output(self) -> None:
        """
        Drain any tell()/write() output the just-completed verb published
        through Kombu, before raw mode re-renders the next prompt.

        Kombu publish→consume has ~5-20ms broker latency, so we wait a brief
        deadline for in-flight messages to arrive, then drain. Without this
        the next prompt races the drain and lands above the verb's output.
        """
        deadline = asyncio.get_event_loop().time() + 0.15
        empty_in_a_row = 0
        while empty_in_a_row < 2 and asyncio.get_event_loop().time() < deadline:
            to_write, events = await self._drain_session_buffer()
            for message in events:
                if message.get("event") == "disconnect":
                    self.is_exiting = True
                    self.disconnect_event.set()
                else:
                    await self._route_event(message)
            for piece in to_write:
                self.writer(piece)
            if to_write or events:
                empty_in_a_row = 0
            else:
                empty_in_a_row += 1
            await asyncio.sleep(0.02)

    def _editor_rejection_pieces(self) -> list[str]:
        """Build the "editor not available" error for raw mode (no TUI)."""
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
        """Write to the asyncssh channel with LF→CRLF translation (raw mode only)."""
        if self._chan is None:
            return
        encoded = text.replace("\n", "\r\n")
        if self._iac_enabled and log.isEnabledFor(logging.DEBUG):
            wire = encoded.encode("utf-8", errors="surrogateescape")
            log.debug("chan_write user=%s len=%d head=%r", self.user.pk, len(wire), wire[:80])
        self._chan.write(encoded)

    def _chan_write_iac(self, data: bytes) -> None:
        """
        Write raw IAC bytes to the asyncssh channel.

        For MUD-client sessions the channel uses UTF-8 with
        ``errors='surrogateescape'``, so we decode the bytes through that
        codec to get a str that re-emits as the original bytes on the
        wire. Used for IAC subnegotiation frames from the ``"oob"`` path.
        """
        if self._chan is None:
            return
        if log.isEnabledFor(logging.DEBUG):
            log.debug("chan_write_iac user=%s bytes=%r", self.user.pk, data)
        try:
            self._chan.write(data.decode("utf-8", errors="surrogateescape"))
        except BrokenPipeError:
            pass

    def _emit_prompt_end_marker(self) -> None:
        """
        Emit ``IAC EOR`` or ``IAC GA`` after a prompt render so MUD clients
        and screen readers can detect the server-to-client turnaround.

        For IAC-capable sessions we always emit a marker, defaulting to GA
        (the MUD convention — Mudlet's mapper auto-detect needs it). EOR is
        used instead when the client explicitly negotiated option 25. For
        vanilla SSH sessions this is a no-op since the bytes would render
        as garbage in a plain terminal.
        """
        if not self._iac_enabled:
            return
        from .iac import encode_eor, encode_ga  # pylint: disable=import-outside-toplevel

        iac = _session_settings.get(self.user.pk, {}).get("iac", {})
        if iac.get("eor"):
            self._chan_write_iac(encode_eor())
        else:
            self._chan_write_iac(encode_ga())

    async def _read_line_raw(self) -> str | None:
        """
        Read one line from the SSH channel in raw mode.

        Buffers plain bytes until CR/LF; drops escape sequences (MUD clients
        do their own line editing). Returns ``None`` on EOF.

        Per telnet RFC defaults the server does not echo input — MUD clients
        (Mudlet, MUSHclient, TinTin++, ...) all local-echo by default and a
        server-side echo would land as a duplicate copy on the user's screen.
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
                            return line
                        if key in (Keys.ControlD,) and not self._raw_line_buffer:
                            return None
                        if key in (Keys.Backspace, Keys.ControlH):
                            if self._raw_line_buffer:
                                self._raw_line_buffer = self._raw_line_buffer[:-1]
                            continue
                        if data and not data.startswith("\x1b"):
                            self._raw_line_buffer += data
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

    async def run_window_session(self, req: dict):
        """
        Enter persistent windowed display mode and run until close/disconnect.

        Launches the full-screen window Application (top region + scrolling
        output + input line), reroutes async output into its scroll buffer
        via :meth:`process_messages`, and returns to the scrolling REPL when
        the window closes. Mirrors :meth:`run_editor_session` for callback
        dispatch.

        :param req: ``window_open`` request dict with ``height``/``title`` and
            optional callback fields
        """
        from django.core.cache import cache

        from .window import WindowState, build_window_app

        settings = _session_settings.setdefault(self.user.pk, {})
        quiet = settings.get("quiet_mode", False)
        state = WindowState(height=req.get("height", 1), title=req.get("title"), quiet=quiet)
        self._window_state = state

        def _on_accept(buff):
            text = buff.text
            get_app().create_background_task(self._window_handle_line(text))
            return False  # clear the input buffer

        window_app = build_window_app(state, _on_accept, style=self.style)
        self._window_app = window_app

        # Mark active both in-process (authoritative for the message loop) and
        # in the cache (so Celery-side verbs can read window state).
        settings["window_active"] = True
        settings["window_height"] = state.height
        settings["window_title"] = state.title
        cache.set(f"moo:session:{self.user.pk}:window_active", True, timeout=86400)

        async def _watch_disconnect():
            await self.disconnect_event.wait()
            try:
                window_app.exit()
            except Exception:  # pylint: disable=broad-except
                pass

        watcher = asyncio.ensure_future(_watch_disconnect())
        try:
            await window_app.run_async()
        finally:
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass
            window_eof = getattr(window_app, "window_eof", False)
            self._window_app = None
            self._window_state = None
            settings["window_active"] = False
            cache.delete(f"moo:session:{self.user.pk}:window_active")
            await self._dispatch_window_close_callback(req)
            # ^D inside window mode = quit the session, not just the window —
            # otherwise the user lands on the scrolling prompt and must ^D
            # again. c-q / c-c still fall through to the REPL (escape hatch).
            if window_eof:
                self.is_exiting = True
                self.disconnect_event.set()

    async def _dispatch_window_close_callback(self, req: dict) -> None:
        """Fire the optional on-close callback verb (wizard-gated)."""
        if not (req.get("callback_this_id") and req.get("callback_verb_name")):
            return
        caller = await sync_to_async(models.Object.objects.get)(pk=req["caller_id"])
        if not await sync_to_async(caller.is_wizard)():
            log.warning("run_window_session: rejected callback with non-wizard caller_id=%s", req["caller_id"])
            return
        tasks.invoke_verb.delay(
            "closed",
            *req.get("args", []),
            caller_id=req["caller_id"],
            player_id=req["player_id"],
            this_id=req["callback_this_id"],
            verb_name=req["callback_verb_name"],
        )

    async def _window_handle_line(self, line: str):
        """
        Run a line typed in window mode through the command pipeline and append
        the result to the window's scroll region.
        """
        from rich.markup import escape

        from .window import render_markup_to_ansi

        if self._window_state is None:
            return
        state = self._window_state
        if line.strip():
            state.append_output(render_markup_to_ansi(f"[grey50]>>> [/grey50]{escape(line)}", state.quiet))
            output_pieces, _events = await self.handle_command(line)
            for piece in output_pieces or []:
                state.append_output(render_markup_to_ansi(piece if isinstance(piece, str) else str(piece), state.quiet))
        if self._window_app is not None:
            self._window_app.invalidate()

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

        :param req: input request dict with keys ``prompt``, ``password``,
            ``callback_this_id``, ``callback_verb_name``, ``caller_id``,
            ``player_id``, and optional ``args``
        """
        while req is not None:
            prompt_text = req.get("prompt", "")
            is_password = req.get("password", False)

            session: PromptSession = PromptSession()
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
        player = self._get_avatar()
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
        player = self._get_avatar()
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
        Build the prompt message tuple as a stable marker.

        Stable prompts make MUD-client mappers and screen readers happy;
        per-room details belong in GMCP Room.Info events (and the room
        description), not in the prompt string.
        """
        return [("class:pound", ">>> ")]

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

        caller = self._get_avatar()
        now = datetime.now(timezone.utc)
        # Rate-limit last_connected_time writes to avoid hammering the DB.
        if self.last_property_write is None or (now - self.last_property_write).total_seconds() > 15:
            with code.ContextManager(caller, lambda x: None, site=self.site):
                caller.set_property("last_connected_time", now)
            self.last_property_write = now
        log.debug(f"{caller}: {line}")

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
            # OSC 133 is shell-integration framing for the scrolling REPL; in
            # window mode the output is appended to the App's scroll region,
            # where the raw ;C/;D markers would render as literal text. Skip it.
            osc133 = self._osc133_enabled() and self._window_state is None
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

    def _try_gmcp_editor_handoff(self, message: dict) -> bool:
        """
        Hand the editor request off to the client via GMCP if it has
        advertised the ``Editor`` package via ``Core.Supports.Set``.

        On success, sends ``Editor.Start { id, content, content_type, title }``
        on the wire and stashes the callback metadata in
        ``_session_settings[user_pk]["pending_edits"][id]`` so the matching
        ``Editor.Save`` (handled in ``server.py``) can dispatch the callback
        verb. Returns ``True`` if the handoff happened (caller should NOT
        also enqueue the prompt-toolkit fallback).
        """
        import uuid  # pylint: disable=import-outside-toplevel

        from .iac import encode_gmcp  # pylint: disable=import-outside-toplevel

        if self.user is None:
            return False
        settings = _session_settings.get(self.user.pk, {})
        iac = settings.get("iac") or {}
        pkgs = iac.get("gmcp_packages") or {}
        if "Editor" not in pkgs:
            return False

        edit_id = uuid.uuid4().hex
        pending = _session_settings.setdefault(self.user.pk, {}).setdefault("pending_edits", {})
        pending[edit_id] = {
            "callback_this_id": message.get("callback_this_id"),
            "callback_verb_name": message.get("callback_verb_name"),
            "caller_id": message.get("caller_id"),
            "player_id": message.get("player_id"),
            "args": message.get("args", []),
        }
        payload = {
            "id": edit_id,
            "content": message.get("content", ""),
            "content_type": message.get("content_type", "text"),
            "title": message.get("title"),
        }
        try:
            self._chan_write_iac(encode_gmcp("Editor.Start", payload))
        except Exception:  # pylint: disable=broad-except
            log.exception("Editor.Start send failed user=%s edit_id=%s", self.user, edit_id)
            pending.pop(edit_id, None)
            return False
        return True

    async def _route_event(self, message):
        """Forward a dict-typed broker event to its matching asyncio queue."""
        kind = message.get("event")
        if kind == "oob":
            payload = message.get("data")
            if isinstance(payload, (bytes, bytearray)):
                self._chan_write_iac(bytes(payload))
            return
        if kind and kind.startswith("window"):
            self._route_window_event(kind, message)
            return
        # Editor / paginator / input prompts are mutually exclusive with window
        # mode (they would fight the full-screen Application for the screen).
        if self._window_state is not None and kind in ("editor", "paginator", "input_prompt"):
            from .window import render_markup_to_ansi  # pylint: disable=import-outside-toplevel

            self._window_state.append_output(
                render_markup_to_ansi("[grey50](not available in window mode)[/grey50]", self._window_state.quiet)
            )
            if self._window_app is not None:
                self._window_app.invalidate()
            return
        if kind == "editor":
            if self._try_gmcp_editor_handoff(message):
                return
            await self.editor_queue.put(message)
        elif kind == "paginator":
            settings = _session_settings.get(self.user.pk, {})
            is_raw = settings.get("mode") == MODE_RAW
            if is_raw:
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

    def _route_window_event(self, kind: str, message: dict) -> None:
        """
        Apply a ``window_*`` broker event.

        ``window_open`` enters window mode via the queue race; the rest mutate
        the live :class:`~moo.shell.window.WindowState` and invalidate. All
        no-op for raw clients (which never enter window mode — GMCP-capable
        MUD clients are served by the ``Window.*`` GMCP push from the SDK).
        """
        if _session_settings.get(self.user.pk, {}).get("mode") == MODE_RAW:
            return
        if kind == "window_open":
            if self._window_state is not None:
                # Already in window mode — treat as a resize.
                self._window_state.set_height(message.get("height", self._window_state.height))
            else:
                self.window_queue.put_nowait(message)
            self._invalidate_window()
            return
        state = self._window_state
        if state is None:
            return
        if kind == "window_write":
            state.write(message.get("row", 0), message.get("col", 0), message.get("text", ""))
        elif kind == "window_cursor":
            state.move_cursor(message.get("row", 0), message.get("col", 0))
        elif kind == "window_emit":
            state.emit(message.get("text", ""))
        elif kind == "window_clear":
            state.clear(message.get("row"))
        elif kind == "window_split":
            state.set_height(message.get("height", state.height))
        elif kind == "window_close":
            if self._window_app is not None:
                self._window_app.exit()
            return
        self._invalidate_window()

    def _invalidate_window(self) -> None:
        """Request a redraw of the window Application if one is running."""
        if self._window_app is not None:
            try:
                self._window_app.invalidate()
            except Exception:  # pylint: disable=broad-except
                pass

    def _window_append(self, pieces, quiet: bool) -> None:
        """Append rendered output pieces to the live window's scroll region."""
        from .window import render_markup_to_ansi  # pylint: disable=import-outside-toplevel

        if self._window_state is None:
            return
        for piece in pieces:
            text = piece if isinstance(piece, str) else str(piece)
            self._window_state.append_output(render_markup_to_ansi(text, quiet))
        self._invalidate_window()

    def writer(self, s, is_error=False):
        """
        Render a Rich markup string to the terminal.

        Quiet mode strips colour; raw-ansi marker values bypass Rich so
        OSC sequences survive intact.

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
        quiet_mode = settings.get("quiet_mode", False)
        color_system: Optional[Literal["truecolor"]] = None if quiet_mode else "truecolor"
        if mode == MODE_RAW:
            console = Console(
                color_system=color_system,
                force_terminal=True,
                no_color=quiet_mode,
            )
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

                    if self._window_state is not None:
                        # Window mode owns the screen: append output to its
                        # scroll buffer and invalidate instead of run_in_terminal
                        # (which would corrupt the alternate screen).
                        self._window_append(to_write, settings.get("quiet_mode", False))
                    elif is_raw:
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
                        color_system: Optional[Literal["truecolor"]] = (
                            None if settings.get("quiet_mode", False) else "truecolor"
                        )
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
