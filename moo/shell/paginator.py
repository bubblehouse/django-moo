# -*- coding: utf-8 -*-
"""
Full-screen read-only paginator for SSH sessions, powered by pypager.
"""

import importlib
import sys

import pygments
import prompt_toolkit
import pypager
from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text import HTML, PygmentsTokens
from pypager.pager import Pager
from pypager.source import FormattedTextSource, StringSource

_LEXERS = {
    "python": ("pygments.lexers", "PythonLexer"),
    "json": ("pygments.lexers", "JsonLexer"),
}

_DISABLED_HANDLERS = frozenset(("_print_filename", "_examine", "_next_file", "_previous_file", "_remove_source"))

_python_version = sys.version_info
_ptk_version = prompt_toolkit.__version__
_pypager_version = pypager.__version__

HELP = (
    HTML("""
            <title>SUMMARY OF COMMANDS</title>

 <keys> h  H             </keys> Display this help.
 <keys> q  Q  ZZ         </keys> Exit.

 <line>------------------------------------------------------</line>

  <subtitle> Moving </subtitle>

 <keys>e  ^E  j  ^N  CR  </keys> Forward one line.
 <keys>y  ^Y  k  ^K  ^P  </keys> Backward one line.
 <keys>f  ^F  ^V  SPACE  </keys> Forward one window.
 <keys>b  ^B  ESC-v      </keys> Backward one window.
 <keys>d  ^D             </keys> Forward one half-window.
 <keys>u  ^U             </keys> Backward one half-window.
 <keys>ESC-)  RightArrow </keys> Left one half screen width.
 <keys>ESC-(  LeftArrow  </keys> Right one half screen width.
 <keys>F                 </keys> Forward forever; like "tail -f"
 <keys>r  R  ^R  ^L      </keys> Repaint screen.

  <subtitle> SEARCHING </subtitle>

 <keys>/pattern          </keys> Search forward.
 <keys>?pattern          </keys> Search backward.
 <keys>n                 </keys> Repeat previous search.
 <keys>N                 </keys> Repeat previous search in reverse direction.
 <keys>ESC-u             </keys> Undo (toggle) search highlighting.

  <subtitle> JUMPING </subtitle>

 <keys> g  &lt;  ESC-&lt;</keys>       Go to the first line in file.
 <keys> G  &gt;  ESC-&gt;</keys>       Go to the last line in file.

 <keys>m&lt;letter&gt;   </keys>       Mark the current position with &lt;letter&gt;
 <keys>'&lt;letter&gt;   </keys>       Go to a previously marked position.
 <keys>^X^X              </keys> Same as <keys>'.</keys>

    A mark is any upper-case or lower-case letter.
    Certain marks are predefined.
        <keys>^</keys>  means  beginning of the file
        <keys>$</keys>  means  end of the file

  <subtitle> Extras </subtitle>

  <keys>w                </keys> Enable/disable <b>line wrapping</b>.

  <subtitle> About Pypager </subtitle>

  Pypager is a <u>prompt_toolkit</u> application.

  - Pypager version:        <version>%s</version>
  - Python version:         <version>%s.%s.%s</version>
  - prompt_toolkit version: <version>%s</version>

""")
    % (
        _pypager_version,
        _python_version[0],
        _python_version[1],
        _python_version[2],
        _ptk_version,
    )
)


async def run_paginator(content: str = "", content_type: str = "text") -> None:
    """
    Display read-only text with less-like pagination in the full-screen terminal.

    :param content: text to display
    :param content_type: "python", "json", or "text" — controls syntax highlighting
    """
    if content_type in _LEXERS:
        module_name, class_name = _LEXERS[content_type]
        lexer_class = getattr(importlib.import_module(module_name), class_name)
        tokens = list(pygments.lex(content, lexer_class()))
        source = FormattedTextSource(PygmentsTokens(tokens))
    else:
        source = StringSource(content)

    import pypager.pager as _pypager_pager

    _pypager_pager.HELP = HELP

    session = get_app_session()
    pager = Pager(input=session.input, output=session.output)

    kb = pager.application.key_bindings
    kb._bindings[:] = [  # pylint: disable=protected-access
        b for b in kb._bindings if b.handler.__name__ not in _DISABLED_HANDLERS  # pylint: disable=protected-access
    ]
    kb._clear_cache()  # pylint: disable=protected-access

    pager.add_source(source)
    await pager.run_async()
