# -*- coding: utf-8 -*-
"""
Prompt-Toolkit interface
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

# Session-specific output settings registry
# Keyed by user_pk, stores {mode, output_prefix, output_suffix, quiet_mode, color_system}
# Settings are cleared when user disconnects
_session_settings: dict[int, dict] = {}

# Shell modes. See MooPromptToolkitSSHSession for how TERM selects one.
MODE_RICH = "rich"
MODE_RAW = "raw"

PROMPT_SHORTCUTS = {
    '"': 'say "%"',
    "'": "say '%'",
    ":": 'emote "%"',
    ";": '@eval "%"',
}


class _RawAnsi(str):
    """
    Marker subclass of str: instances are emitted to the terminal verbatim
    by ``MooPrompt.writer``, bypassing Rich rendering. Used for OSC 133
    sequences that Rich would otherwise escape.
    """


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

    Creates a MooPrompt instance and runs the command and message processing
    coroutines concurrently until either exits.

    :param user: the authenticated Django user whose avatar will be the active player
    :param session: the asyncssh session; its ``_chan`` is the channel the
        raw-mode loop reads from and writes to. Not used in rich mode.
    :param mode: ``"rich"`` (default) or ``"raw"``.
    :param automation: if True, disables interactive shortcuts (e.g. ``"`` → say).
        Always paired with ``mode="rich"``.
    """
    repl = MooPrompt(user, session=session, mode=mode, automation=automation)
    repl_tasks = [asyncio.ensure_future(f()) for f in (repl.process_commands, repl.process_messages)]
    try:
        # FIRST_COMPLETED so that when either coroutine exits we immediately
        # tear down the other rather than leaking it. ALL_COMPLETED kept both
        # running forever when SSH channel close failed to propagate EOF to
        # prompt_async — process_messages stayed in its loop, holding the
        # session's Kombu consumer open. A new connection for the same user
        # then added a second consumer on the same queue, round-robin-splitting
        # confunc messages between the zombie and the live session.
        await asyncio.wait(repl_tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        repl.is_exiting = True
        repl.disconnect_event.set()
        for task in repl_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*repl_tasks, return_exceptions=True)
        # Guarantee the Kombu consumer is released even if a task was
        # cancelled before its own teardown could run.
        await repl._close_session_buffer()  # pylint: disable=protected-access


class MooPrompt:
    """
    Interactive prompt session for a connected MOO user.

    Manages two concurrent async loops: one that reads user input and dispatches
    commands, and one that polls the message queue and prints output sent to the
    user from the MOO world. Editor and paginator requests are routed through
    dedicated asyncio queues so they can interrupt the input prompt cleanly.
    """

    # Source of truth for prompt colours. Both ``style`` (prompt_toolkit, rich
    # mode) and ``_render_prompt_tuples`` (Rich, raw mode) derive from this so
    # the two modes render the same palette.
    _PROMPT_PALETTE = {
        "": "#ffffff",  # user input / default text
        "name": "#884444",
        "at": "#00aa00",
        "colon": "#0000aa",
        "pound": "#00aa00",
        "location": "#00aa55",
    }

    style = Style.from_dict(_PROMPT_PALETTE)

    def __init__(self, user, session=None, mode: str = MODE_RICH, automation: bool = False):
        """
        Initialize the prompt session for the given Django user.

        :param user: the authenticated Django user whose avatar will be the active player
        :param session: the asyncssh session; used by raw mode to reach ``_chan``
        :param mode: ``"rich"`` (prompt_toolkit) or ``"raw"`` (line I/O)
        :param automation: if True, disables interactive shortcuts
        """
        self.user = user
        self.mode = mode
        self._chan = getattr(session, "_chan", None) if session is not None else None
        self.automation = automation
        self.is_exiting = False
        # _session_settings is populated in _repl_setup() (after clearing
        # anything stale from a previous connection on the same account).
        # We still write the mode here so code paths that construct a
        # MooPrompt without running the REPL (e.g. unit tests) can observe
        # the mode immediately.
        _session_settings.setdefault(self.user.pk, {})["mode"] = mode
        if automation:
            _session_settings[self.user.pk]["automation"] = True
        self.editor_queue: asyncio.Queue = asyncio.Queue()
        self.paginator_queue: asyncio.Queue = asyncio.Queue()
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.disconnect_event = asyncio.Event()
        # Set by _repl_setup once the session buffer is open and confunc has
        # finished publishing. process_messages waits on this before draining
        # so the confunc burst is available on the first drain call.
        self.startup_drain_complete = asyncio.Event()
        # Set by the rich prompt's pre_run callback when the first Application
        # has started. process_messages waits on this too because
        # run_in_terminal only routes output correctly while an Application
        # is active — calling it earlier drops messages into
        # print_formatted_text's default AppSession, which is not wired to
        # the SSH channel. In raw mode (no Application), this event is set
        # at the top of process_commands_raw.
        self.prompt_app_ready = asyncio.Event()
        # Tracks whether the next render should emit OSC 133 ;A/;B markers.
        # prompt_toolkit performs TWO renders at Application startup (app
        # setup + first full render) on the same physical line — both
        # emitting markers makes iTerm display two prompt regions on one
        # line. We emit once per "logical prompt appearance": initial
        # prompt, and the re-render that follows any ``run_in_terminal``
        # call that moves the prompt down. ``_run_in_terminal_marked``
        # flips this back to True when the prompt needs a new anchor.
        self._osc_needs_markers = [True]
        # Rich-rendered ANSI string holding the connect-time confunc burst.
        # Populated by _repl_setup, consumed by the rich-mode pre_run
        # callback which writes it through the Application's own output
        # (so CPR and render geometry stay consistent). Raw mode consumes
        # it directly via _chan_write at the top of process_commands_raw.
        self._pending_connect_output: str = ""
        # Kombu connection/channel/buffer opened once in _repl_setup and reused
        # by the startup drain and process_messages. The queue is declared with
        # auto_delete=True, so the first consumer keeps it alive; if we let the
        # consumer close between the startup drain and process_messages, the
        # queue vanishes and any tell() published in that window is dropped at
        # the exchange. Holding one buffer open end-to-end avoids that race.
        self._session_conn: Any = None
        self._session_channel: Any = None
        self._session_buffer: Any = None
        self.last_property_write: datetime | None = None

        # Connection-level output configuration (session-only, not persisted)
        self.output_prefix = None  # Set by PREFIX verb
        self.output_suffix = None  # Set by SUFFIX verb
        self.quiet_mode = False  # Set by QUIET verb
        self.color_system = "truecolor"  # Default: full color support

        # Buffer for raw-mode line input. Populated via the PipeInput the
        # contrib SSH session wires up around us.
        self._raw_line_buffer: str = ""

    def _osc133_enabled(self) -> bool:
        return _session_settings.get(self.user.pk, {}).get("osc133_mode", True)

    def _prefixes_enabled(self) -> bool:
        return _session_settings.get(self.user.pk, {}).get("prefixes_mode", False)

    def _make_osc_pre_run(self, prompt_session):
        """
        Build a ``pre_run`` callback that wires OSC 133 ;A/;B emission into
        the rich-mode prompt's render events.

        prompt_toolkit creates a fresh ``Application`` per ``prompt_async``
        call (accessible as ``prompt_session.app`` once ``pre_run`` fires).
        ``before_render``/``after_render`` handlers emit ;A and ;B — but
        only once per *logical* prompt appearance. Emitting on every
        render duplicates markers within a single input cycle (app setup
        does two renders on the same line) and iTerm renders them as two
        stacked prompts.

        The ``_osc_needs_markers`` flag is reset to True by
        ``_run_in_terminal_marked`` so that re-renders caused by async
        tells (which push the prompt down to a NEW screen position) get
        a fresh anchor at the new location. Keystroke-driven redraws
        (same position) skip emission because the flag stays False.

        Safe against the original "command indicator on every line" bug
        because the markers are emitted from render events rather than
        baked into the prompt's FormattedText.
        """

        def pre_run():
            # Drain any pending connect-time confunc output BEFORE the first
            # render so the prompt lands below it. Going through
            # ``app.output.write_raw`` keeps the write on prompt_toolkit's
            # output pipeline, so CPR and renderer state are consistent.
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
                    self._osc_needs_markers[0] = False
                except Exception:  # pylint: disable=broad-except
                    pass

            prompt_session.app.before_render += before_render
            prompt_session.app.after_render += after_render
            # Signal process_messages that an Application is live and
            # run_in_terminal will route output correctly.
            self.prompt_app_ready.set()

        return pre_run

    async def _run_in_terminal_marked(self, fn):
        """
        Run ``fn`` inside prompt_toolkit's ``run_in_terminal`` context and
        signal that the next prompt render is a NEW anchor position.

        Use this instead of calling ``run_in_terminal`` directly when the
        callable emits output above the prompt: the prompt scrolls down,
        so a fresh OSC 133 ;A/;B pair should mark its new location. For
        non-display work inside ``run_in_terminal`` (rare), keep using the
        raw function.
        """
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
        Shared REPL startup: mark the player connected, fire confunc, stamp
        session settings so Celery workers can read the mode.

        Called at the top of both ``process_commands_rich`` and
        ``process_commands_raw``. Clears any session settings left over from a
        previous connection on the same account (e.g. an agent that enabled
        QUIET / OUTPUTPREFIX) before re-stamping ``mode`` and ``automation``.
        """
        from django.core.cache import cache

        _session_settings.pop(self.user.pk, None)
        _session_settings.setdefault(self.user.pk, {})["mode"] = self.mode
        if self.automation:
            _session_settings[self.user.pk]["automation"] = True
        # Mirror the mode into the Django cache so out-of-process verbs
        # (Celery workers) can read it via get_client_mode().
        cache.set(f"moo:session:{self.user.pk}:mode", self.mode, timeout=86400)
        await self._mark_connected()
        # Open the player's message-queue consumer BEFORE firing confunc so
        # the queue is declared and bound while the first tell() runs. With
        # ``auto_delete=True`` the queue exists only while at least one
        # consumer is attached; if we declared it only at drain time, any
        # tell() published between task dispatch and drain start would be
        # dropped at the exchange (no matching queue → nowhere to route).
        # The buffer is held open for the life of the session and drained
        # by ``process_messages`` once the prompt Application is running.
        await self._open_session_buffer()
        confunc_tasks = await self._fire_confunc()
        await self._await_tasks(confunc_tasks)
        # Drain the connect-time confunc burst and hand the rendered ANSI
        # off to ``self._pending_connect_output``. The rich-mode ``pre_run``
        # callback writes it to ``app.output`` — prompt_toolkit's own
        # output pipeline — so the description appears above the prompt
        # AND prompt_toolkit's CPR / renderer state stays consistent.
        # Writing directly to the SSH channel (bypassing prompt_toolkit)
        # works but races the Application's CPR query, producing a
        # "your terminal doesn't support CPR" warning even on iTerm.
        # Raw mode consumes the buffer via ``_chan_write`` at the top of
        # ``process_commands_raw`` — there is no Application there.
        #
        # Short coalescing loop: Redis round-trip latency can split a
        # single confunc's tell() burst across two consumer reads.
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
        """
        Shared REPL shutdown: signal messages loop to exit, fire disfunc, and
        clear session settings / cache keys.

        Always runs in the ``finally`` of both command loops so the two
        coroutines terminate together and leave no zombie state behind.
        """
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
        Read and dispatch user input in a loop using prompt_toolkit.

        Waits simultaneously for a typed command, an editor request, or a
        paginator request. Whichever arrives first is handled; the others are
        cancelled. Exits cleanly on EOF or KeyboardInterrupt.
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
                    # Emit OSC 133 ;A and ;B exactly once per input cycle by
                    # writing them via the Application's render events. Putting
                    # them in the prompt's FormattedText caused them to be
                    # re-emitted on every prompt redraw — and run_in_terminal
                    # redraws the prompt after every async tell, which a
                    # screen reader interprets as a new command boundary per
                    # line. before_render fires before the prompt content is
                    # written to the output buffer (so ;A lands at the start
                    # of the prompt region) and after_render fires after (so
                    # ;B lands between the prompt text and user input).
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
                        # The editor TUI cannot run in automation mode — doing so
                        # hangs app.run_async() waiting for keystrokes that never
                        # arrive, which corrupts the run_in_terminal Future chain
                        # and breaks every subsequent command in the session.
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
                        # If the verb published an event, process_messages will
                        # route it to the matching asyncio queue momentarily.
                        # Wait for it directly and dispatch — skipping the
                        # prompt_async race avoids the MOO prompt flashing
                        # between the verb and its continuation.
                        await self._dispatch_pending_event(events)
        except:  # pylint: disable=bare-except
            log.exception("Error in command processing")
        finally:
            await self._repl_teardown()
        log.debug("REPL is exiting, stopping main thread...")

    async def process_commands_raw(self):
        """
        Read and dispatch user input in a loop with plain line I/O.

        Used by MUD clients that send ``TERM=xterm-256-basic``. No
        prompt_toolkit, no cursor manipulation — the prompt is written once
        per turn and async output just lands on new lines. TUI editor requests
        are rejected with a hint pointing at the inline ``@edit … with "…"``
        form; paginator requests never arrive because ``process_messages``
        dumps them inline in raw mode.
        """
        await self._repl_setup()
        # Raw mode has no prompt_toolkit Application, so emit any pending
        # connect-time confunc output directly to the channel here.
        if self._pending_connect_output:
            self._chan_write(self._pending_connect_output)
            self._pending_connect_output = ""
        # process_messages gates on prompt_app_ready to avoid writing into
        # a dead AppSession in rich mode. Set it here so raw-mode drains
        # start immediately.
        self.prompt_app_ready.set()
        try:
            while not self.is_exiting:
                prompt_tuples = await self.generate_prompt()
                rendered = self._render_prompt_tuples(prompt_tuples)
                if self._osc133_enabled():
                    rendered = OSC_133_PROMPT_START + rendered + OSC_133_COMMAND_START
                self._chan_write(rendered)
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
                    # Raw mode dumps paginator events in process_messages, so
                    # we should never land here. If we do, log and fall back
                    # to a straight dump — the gating in process_messages has
                    # drifted from the mode state and should be investigated.
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
        """
        Build the "editor not available" error the REPL writes when a
        verb-initiated editor event arrives in a mode that cannot open the
        TUI (automation or raw). Wrapped in global prefix/suffix so
        delimiter-driven clients parse the reply cleanly.
        """
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
        """
        Render ``generate_prompt()`` tuples to an ANSI string suitable for
        direct writing to the SSH channel in raw mode.

        Each tuple is ``(style_class, text)``; the ``class:xxx`` prefix is
        stripped and looked up in ``_PROMPT_PALETTE`` so raw-mode prompts
        match the colours rich-mode clients see via ``print_formatted_text``.
        """
        console = Console(color_system="truecolor", force_terminal=True)
        with console.capture() as capture:
            for style_class, text in tuples:
                key = style_class[len("class:") :] if style_class.startswith("class:") else style_class
                colour = self._PROMPT_PALETTE.get(key)
                console.print(text, end="", style=colour)
        return capture.get()

    def _chan_write(self, text: str) -> None:
        """
        Write text directly to the asyncssh channel, converting LF to CRLF.

        Only used from the raw-mode path — rich mode goes through
        ``print_formatted_text`` which handles newlines itself.
        """
        if self._chan is None:
            # Defensive: tests may construct a MooPrompt without a session.
            return
        self._chan.write(text.replace("\n", "\r\n"))

    async def _read_line_raw(self) -> str | None:
        """
        Read one line of input from the SSH channel in raw mode.

        Consumes keys from the prompt_toolkit PipeInput the contrib SSH
        session wires up around us, buffering until CR or LF. Returns the
        decoded line without trailing CR/LF. Returns ``None`` on EOF.

        Escape sequences (arrow keys, function keys, bracketed-paste
        envelopes — anything whose data starts with ``\\x1b``) are dropped on
        the floor. This is deliberate: traditional MUD clients do their own
        line editing and history; the server-side reader just buffers plain
        bytes. If a future client needs server-side line editing in raw
        mode, that's a separate feature.
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

    async def _dispatch_pending_event(self, events: list) -> None:
        """
        If ``events`` indicates the just-finished verb published an editor,
        paginator, or input_prompt message, wait briefly for it to arrive on the
        matching asyncio queue and dispatch directly to the handler. This bypasses
        the ``prompt_async`` race in ``process_commands`` so the MOO prompt does
        not flash between a verb and its continuation.

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

        After the callback verb is dispatched, loops briefly on ``input_queue`` to
        absorb any follow-up ``input_prompt`` event emitted by the callback. This
        keeps the whole input chain inside one session so the MOO prompt is not
        re-rendered between stages.

        In automation mode the prompt is skipped and the callback is not invoked
        (automation clients should pass arguments directly as verb arguments).

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
    def handle_command(self, line: str) -> tuple[list, list]:
        """
        Parse the command and execute it.

        Updates ``last_connected_time`` on the avatar at most once every 15 seconds
        to avoid excessive property writes. Any exception from the Celery task is
        caught and rendered as a red traceback in the terminal.

        :param line: raw input string typed by the user
        :returns: ``(to_write, events)`` — list of Rich markup strings to write to
            the terminal (delivered via ``run_in_terminal`` by the caller), and a
            list of event-type strings (``"input_prompt"``, ``"editor"``,
            ``"paginator"``) published by the verb during its Celery task.
        """
        from django.core.cache import cache

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
        # Only wrap with prefix/suffix delimiters when there is actual content.
        # Sending empty-content delimiter frames in automation mode leaves an
        # unresolved run_in_terminal future and hangs process_commands.
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
        """
        Open the player's message-queue consumer for the life of the session.

        The queue binds with ``auto_delete=True``, so the broker keeps it alive
        only while at least one consumer is attached. Opening the buffer here
        — before the first confunc tell() runs — guarantees the queue exists
        when those messages are published, so the exchange has somewhere to
        route them. The buffer is closed in ``_repl_teardown``.
        """
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
        Drain all pending Kombu messages from the session buffer.

        Session setting events are applied in-place; printable messages are
        returned for the caller to render. Used by the startup drain in
        ``_repl_setup``, by the ``.flush`` command, and by ``process_messages``
        — all three share the single session consumer so the auto_delete queue
        never disappears mid-session and messages are never round-robin split
        across multiple consumers.
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
        """
        Drain printable messages from the session buffer (``.flush`` command).

        Event-typed messages (editor, paginator, input_prompt) encountered
        during this drain are routed to their asyncio queues just as
        ``process_messages`` would have done — this keeps editor/paginator
        state consistent even when the user explicitly asks for a flush.
        """
        to_write, events = await self._drain_session_buffer()
        for message in events:
            await self._route_event(message)
        return to_write

    async def _route_event(self, message):
        """
        Forward a dict-typed broker message to its matching asyncio queue.

        Shared by ``process_messages`` and ``_drain_messages`` so both paths
        handle editor / paginator / input_prompt events the same way.
        """
        kind = message.get("event")
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
        Render a Rich markup string to the terminal.

        In rich mode, captures Rich's ANSI output and passes it through
        ``print_formatted_text`` so it prints above the active input prompt
        without clobbering it.

        In raw mode, writes the captured ANSI bytes directly to the SSH
        channel with LF→CRLF translation, bypassing prompt_toolkit entirely.
        Rich only emits SGR colour sequences (no cursor control), so the
        output is safe for traditional MUD clients.

        In quiet mode, colors are disabled at the Rich level so no ANSI escape
        sequences are emitted — automation clients receive clean plain text.

        :param s: Rich markup string to render
        :param is_error: reserved for future use; currently unused
        """
        is_raw_ansi = isinstance(s, _RawAnsi)
        if not isinstance(s, str):
            s = str(s)
        settings = _session_settings.get(self.user.pk, {})
        mode = settings.get("mode", MODE_RICH)
        if is_raw_ansi:
            # Bypass Rich AND prompt_toolkit's ANSI parser entirely — the
            # parser silently consumes the `\x1b]` OSC introducer and emits a
            # malformed sequence. Use prompt_toolkit's [ZeroWidthEscape] style
            # in rich mode (designed for OSC pass-through) and direct channel
            # write in raw mode.
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
        Poll the Kombu message queue and display incoming MOO output.

        Runs in a loop alongside process_commands. ``editor``, ``paginator``,
        and ``input_prompt`` events are forwarded to the appropriate asyncio
        queues; plain string messages are printed via writer.

        Drains through the shared session buffer opened in ``_repl_setup``.
        ``@sync_to_async`` serializes access with any other caller
        (``_repl_setup`` startup drain, ``.flush``) so the single consumer
        never sees racing ``get_nowait`` calls.

        The ``finally`` block signals ``process_commands`` to exit whenever
        this coroutine ends — whether by normal exit, exception, or
        ``disconnect`` event — so the two tasks always terminate together.
        """
        try:
            await asyncio.wait_for(self.startup_drain_complete.wait(), timeout=8.0)
        except asyncio.TimeoutError:
            log.warning("startup_drain_complete not set after 8s — proceeding anyway")
        try:
            # Wait for the prompt Application to be live (rich mode) or for
            # the raw-mode loop to signal readiness. Draining before this
            # point in rich mode would route through ``print_formatted_text``
            # without a live AppSession wired to the SSH channel, dropping
            # the confunc burst on the floor.
            await asyncio.wait_for(self.prompt_app_ready.wait(), timeout=8.0)
        except asyncio.TimeoutError:
            log.warning("prompt_app_ready not set after 8s — proceeding anyway")
        try:
            while not self.is_exiting:
                # asyncssh does not always surface channel close to the
                # prompt_toolkit Application — prompt_async can hang
                # indefinitely on a dead channel, which would keep both REPL
                # coroutines (and the session's Kombu consumer) alive after
                # the client has disconnected. Poll the channel state so the
                # message loop notices and triggers shared teardown.
                if self._chan is not None and self._chan.is_closing():
                    self.is_exiting = True
                    self.disconnect_event.set()
                    break
                to_write, events = await self._drain_session_buffer()
                # Coalesce stragglers from the same tell burst so we do one
                # run_in_terminal for the whole batch instead of one per
                # message (each triggers a prompt re-render — users see the
                # prompt flashing between every line of the confunc output
                # otherwise). Keep polling until the drain returns empty,
                # then stop; the wait is short enough to stay responsive.
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
                        # Assemble every piece into ONE Rich-rendered ANSI
                        # blob and emit it via a single ``print_formatted_text``
                        # call inside a single ``run_in_terminal`` hop.
                        # Calling ``writer`` once per piece caused
                        # prompt_toolkit to re-render the prompt between
                        # every line of the confunc burst (each render emits
                        # a fresh OSC 133 ;A/;B pair), producing the
                        # flashing-prompt-between-lines output that a screen
                        # reader treats as N separate commands.
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
            # Signal process_commands to exit. If this coroutine crashes
            # (e.g. broker disconnect), process_commands would otherwise spin
            # forever waiting for input, keeping the SSH channel open as a
            # zombie. Setting is_exiting + disconnect_event ensures it wakes
            # up and exits cleanly regardless of how we got here.
            self.is_exiting = True
            self.disconnect_event.set()
        log.debug("REPL is exiting, stopping messages thread...")
