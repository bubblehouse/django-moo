# -*- coding: utf-8 -*-
"""
Persistent windowed display mode for rich SSH sessions.

Provides a full-screen ``prompt_toolkit`` layout with three stacked regions:

1. a fixed, cursor-addressable **top region** (a status bar / ASCII map),
2. a **scrolling output region** showing normal game/tell output,
3. a single-line **input region** that feeds the usual command pipeline.

The driver (``moo/shell/prompt.py``) owns the queue, the input bridge, and the
output rerouting; this module only models the screen state and builds the
``Application``. It mirrors the role ``editor.py`` / ``paginator.py`` play for
their TUIs.
"""

from __future__ import annotations

from collections import deque

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import TextArea
from rich.console import Console
from rich.text import Text

#: Cap on retained scrollback lines (the visible slice is always the tail).
_SCROLL_MAXLEN = 2000


def render_markup_to_ansi(markup: str, quiet: bool = False) -> str:
    """
    Render a Rich-markup string to an ANSI string.

    Mirrors the rendering in ``MooPrompt.writer`` / ``process_messages`` so
    window output matches the normal scrolling shell. ``quiet`` strips colour
    for accessibility.

    :param markup: Rich markup (e.g. ``"[bold red]hi[/bold red]"``)
    :param quiet: when True, render without colour
    """
    console = Console(color_system=None if quiet else "truecolor", force_terminal=True)
    with console.capture() as capture:
        console.print(markup, end="")
    return capture.get()


class WindowState:
    """
    Mutable screen state shared between the driver and the Application.

    The top region is a sparse grid of cells keyed by ``(row, col)`` holding
    Rich markup. ``window_write`` sets a cell directly; ``window_cursor`` +
    ``window_emit`` provide a stateful cursor for translating ``set_cursor`` +
    ``print`` sequences. The scroll region is a bounded list of pre-rendered
    ANSI lines; the visible slice is always the tail that fits.

    Overlapping writes on a row are laid left-to-right by column; partial
    mid-segment overwrite is not modelled in v1 (writes at distinct columns,
    the common case, compose correctly).
    """

    def __init__(self, height: int = 1, title: str | None = None, quiet: bool = False):
        self.height = max(1, int(height))
        self.title = title
        self.quiet = quiet
        self.closed = False
        self.cursor = (0, 0)
        self.cells: dict[tuple[int, int], str] = {}
        self.scroll_lines: deque[str] = deque(maxlen=_SCROLL_MAXLEN)

    # -- top region -------------------------------------------------------

    def write(self, row: int, col: int, text: str) -> None:
        """Place ``text`` (markup) at ``(row, col)`` and park the cursor after it."""
        row, col = int(row), int(col)
        self.cells[(row, col)] = str(text)
        self.cursor = (row, col + len(Text.from_markup(str(text)).plain))

    def move_cursor(self, row: int, col: int) -> None:
        """Move the emit cursor to ``(row, col)``."""
        self.cursor = (int(row), int(col))

    def emit(self, text: str) -> None:
        """Write ``text`` at the cursor and advance it (newlines wrap to col 0)."""
        text = str(text)
        row, col = self.cursor
        for i, segment in enumerate(text.split("\n")):
            if i > 0:
                row, col = row + 1, 0
            if segment:
                self.cells[(row, col)] = segment
                col += len(Text.from_markup(segment).plain)
        self.cursor = (row, col)

    def clear(self, row: int | None = None) -> None:
        """Clear the whole top region, or a single ``row``."""
        if row is None:
            self.cells.clear()
            self.cursor = (0, 0)
        else:
            for key in [k for k in self.cells if k[0] == int(row)]:
                del self.cells[key]

    def set_height(self, height: int) -> None:
        """Resize the top region to ``height`` rows."""
        self.height = max(1, int(height))

    def render_top(self) -> str:
        """Composite the top grid into an ANSI block of ``height`` rows."""
        lines = []
        for r in range(self.height):
            segments = sorted(((c, m) for (rr, c), m in self.cells.items() if rr == r), key=lambda s: s[0])
            pieces: list[str] = []
            pos = 0
            for col, markup in segments:
                if col > pos:
                    pieces.append(" " * (col - pos))
                    pos = col
                pieces.append(markup)
                pos += len(Text.from_markup(markup).plain)
            lines.append("".join(pieces))
        return render_markup_to_ansi("\n".join(lines), self.quiet)

    # -- scroll region ----------------------------------------------------

    def append_output(self, ansi_text: str) -> None:
        """Append already-ANSI-rendered output, split into lines."""
        for line in ansi_text.split("\n"):
            self.scroll_lines.append(line)

    def render_scroll(self, visible: int) -> str:
        """Return the last ``visible`` scroll lines as ANSI."""
        if visible <= 0:
            return ""
        tail = list(self.scroll_lines)[-visible:]
        return "\n".join(tail)


def build_window_app(state: WindowState, on_accept, style=None) -> Application:
    """
    Build the full-screen windowed-display Application.

    :param state: the shared :class:`WindowState`
    :param on_accept: sync ``Buffer`` accept handler ``(buffer) -> bool`` that
        bridges the typed line to the command pipeline (returns ``False`` so
        the input buffer clears)
    :param style: optional prompt_toolkit ``Style`` (the driver passes its own
        palette so colours match the normal shell)
    """

    def _top_height() -> Dimension:
        return Dimension.exact(state.height)

    top_window = Window(
        FormattedTextControl(lambda: ANSI(state.render_top()), focusable=False),
        height=_top_height,
        wrap_lines=False,
        style="class:window.top",
    )

    def _render_scroll():
        size = get_app().output.get_size()
        visible = max(1, size.rows - state.height - 1)
        return ANSI(state.render_scroll(visible))

    scroll_window = Window(FormattedTextControl(_render_scroll, focusable=False), wrap_lines=True)

    input_area = TextArea(
        height=1,
        multiline=False,
        wrap_lines=False,
        prompt=">>> ",
        accept_handler=on_accept,
        style="class:window.input",
    )

    kb = KeyBindings()

    @kb.add("c-q")
    @kb.add("c-c")
    def _close(event):
        # Leave window mode and return to the scrolling REPL (escape hatch).
        event.app.exit()

    @kb.add("c-d")
    def _eof_quit(event):
        # EOF on an empty line: quit the whole session, not just the window.
        # In a persistent windowed game the prompt lives inside the window, so
        # the user pressing ^D means "I'm done" — dropping them to a second
        # (scrolling) prompt that needs another ^D is surprising. The driver
        # reads ``window_eof`` after run_async() and signals a disconnect.
        if not input_area.text:
            event.app.window_eof = True  # type: ignore[attr-defined]
            event.app.exit()

    layout = Layout(HSplit([top_window, scroll_window, input_area]), focused_element=input_area)
    app: Application = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        mouse_support=False,
        style=style,
    )
    # Expose the input area so the driver can clear it after dispatch.
    app.window_input_area = input_area  # type: ignore[attr-defined]
    # Set by the c-d binding so run_window_session can turn a window-mode EOF
    # into a full session disconnect rather than a return to the REPL.
    app.window_eof = False  # type: ignore[attr-defined]
    return app
