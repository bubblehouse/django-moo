# -*- coding: utf-8 -*-
"""
Full-screen read-only paginator for SSH sessions.
"""

import importlib

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import style_from_pygments_cls
from prompt_toolkit.widgets import Frame
from pygments.styles import get_style_by_name

_LEXERS = {
    "python": ("pygments.lexers", "PythonLexer"),
    "json": ("pygments.lexers", "JsonLexer"),
}

_TITLES = {
    "python": "Python Viewer",
    "json": "JSON Viewer",
    "text": "Viewer",
}


async def run_paginator(content: str = "", content_type: str = "text") -> None:
    """
    Display read-only text with less-like pagination in the full-screen terminal.

    :param content: text to display
    :param content_type: "python", "json", or "text" — controls syntax highlighting
    """
    lexer = None
    if content_type in _LEXERS:
        module_name, class_name = _LEXERS[content_type]
        lexer_class = getattr(importlib.import_module(module_name), class_name)
        lexer = PygmentsLexer(lexer_class)

    buf = Buffer(document=Document(content), read_only=True)

    kb = KeyBindings()

    @kb.add("q")
    @kb.add("Q")
    def quit(event):
        event.app.exit()

    content_window = Window(
        content=BufferControl(buffer=buf, lexer=lexer),
        wrap_lines=True,
        scrollbar=True,
    )
    status_bar = Window(
        FormattedTextControl("Press [Q] to quit"),
        height=1,
        style="reverse",
    )
    layout = Layout(HSplit([Frame(content_window, title=_TITLES.get(content_type, "Viewer")), status_bar]))
    pygments_style = style_from_pygments_cls(get_style_by_name("solarized-dark"))
    app = Application(layout=layout, key_bindings=kb, full_screen=True, style=pygments_style)

    await app.run_async()
