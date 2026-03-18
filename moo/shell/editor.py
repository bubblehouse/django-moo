# -*- coding: utf-8 -*-
"""
Full-screen text editor for SSH sessions.
"""

import importlib

from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import style_from_pygments_cls
from prompt_toolkit.widgets import Frame, TextArea
from pygments.styles import get_style_by_name

_LEXERS = {
    "python": ("pygments.lexers", "PythonLexer"),
    "json": ("pygments.lexers", "JsonLexer"),
}

_TITLES = {
    "python": "Python Editor",
    "json": "JSON Editor",
    "text": "Editor",
}


async def run_editor(initial_text: str = "", content_type: str = "text", title: str | None = None) -> str | None:
    """
    Display a full-screen text editor over the SSH terminal and return the final
    text, or None if the user cancels.

    :param initial_text: initial buffer contents
    :param content_type: "python", "json", or "text" — controls syntax highlighting
    :param title: optional frame title; defaults to a content_type label
    """
    lexer = None
    if content_type in _LEXERS:
        module_name, class_name = _LEXERS[content_type]
        lexer_class = getattr(importlib.import_module(module_name), class_name)
        lexer = PygmentsLexer(lexer_class)

    editor = TextArea(
        text=initial_text,
        multiline=True,
        wrap_lines=True,
        scrollbar=True,
        lexer=lexer,
    )

    result = {"text": None}
    state = {"confirming": None}  # "save", "cancel", or None

    is_confirming = Condition(lambda: state["confirming"] is not None)
    not_confirming = ~is_confirming

    kb = KeyBindings()

    @kb.add("c-s", filter=not_confirming)
    def request_save(event):
        state["confirming"] = "save"

    @kb.add("c-c", filter=not_confirming)
    @kb.add("c-q", filter=not_confirming)
    def request_cancel(event):
        state["confirming"] = "cancel"

    @kb.add("y", filter=is_confirming)
    @kb.add("Y", filter=is_confirming)
    def confirm(event):
        if state["confirming"] == "save":
            result["text"] = editor.text
        event.app.exit()

    @kb.add("n", filter=is_confirming)
    @kb.add("N", filter=is_confirming)
    @kb.add("escape", filter=is_confirming)
    def deny(event):
        state["confirming"] = None

    def get_status_text():
        if state["confirming"] == "save":
            return "Save changes? [Y]es / [N]o"
        elif state["confirming"] == "cancel":
            return "Discard changes and exit? [Y]es / [N]o"
        return "[Ctrl+S] Save  [Ctrl+C/Q] Cancel"

    status_bar = Window(
        FormattedTextControl(get_status_text),
        height=1,
        style="reverse",
    )
    layout = Layout(HSplit([Frame(editor, title=title if title is not None else _TITLES.get(content_type, "Editor")), status_bar]))
    pygments_style = style_from_pygments_cls(get_style_by_name("solarized-dark"))
    app = Application(layout=layout, key_bindings=kb, full_screen=True, style=pygments_style)

    await app.run_async()
    return result["text"]
