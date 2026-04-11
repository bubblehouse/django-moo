#!moo verb WRAP --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Show or set the terminal wrap column.

Usage:
    WRAP          Show current setting and effective width
    WRAP auto     Use the actual terminal width (default)
    WRAP 120      Set to a fixed number of columns

The setting persists across sessions. When set to 'auto', the server
detects your terminal width at connect time and updates it on resize.

See also: QUIET, PREFIX, SUFFIX
"""

from moo.sdk import context, get_wrap_column
from moo.core import NoSuchPropertyError

if context.parser.has_dobj_str():
    arg = context.parser.get_dobj_str().strip().lower()
    if arg == "auto":
        context.player.set_property("wrap_column", "auto")
        print(f"Wrap column set to auto (currently {get_wrap_column()} columns).")
    else:
        try:
            cols = int(arg)
            if cols < 20 or cols > 500:
                print("Wrap column must be between 20 and 500.")
            else:
                context.player.set_property("wrap_column", cols)
                print(f"Wrap column set to {cols}.")
        except ValueError:
            print(f"Unknown argument: {arg!r}. Use 'auto' or a number (e.g. WRAP 120).")
else:
    try:
        setting = context.player.get_property("wrap_column")
    except NoSuchPropertyError:
        setting = "auto"
    effective = get_wrap_column()
    if setting == "auto":
        print(f"Wrap column: auto ({effective} columns from terminal).")
    else:
        print(f"Wrap column: {setting} columns (fixed).")
