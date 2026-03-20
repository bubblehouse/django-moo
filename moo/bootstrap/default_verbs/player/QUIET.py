#!moo verb QUIET --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Toggle quiet mode for machine-readable output.

Usage:
    QUIET enable    Enable quiet mode (suppresses colors and simplifies prompt)
    QUIET disable   Disable quiet mode
    QUIET           Show current setting

Quiet mode disables Rich color markup in command output and simplifies the
prompt to a bare "$". This is intended for use by machine clients that need
clean plain-text output without ANSI escape sequences.

The setting is session-specific and will be cleared when you disconnect.

Example:
    QUIET on
    look
    The Laboratory
    ...         (no color codes)

See also: PREFIX, SUFFIX
"""

from moo.sdk import get_session_setting, set_session_setting, context

if context.parser.has_dobj_str():
    arg = context.parser.get_dobj_str().lower()

    if arg == "enable":
        set_session_setting("quiet_mode", True)
        print("Quiet mode enabled")
    elif arg == "disable":
        set_session_setting("quiet_mode", False)
        print("Quiet mode disabled")
    else:
        print(f"Unknown argument: {arg!r}. Use 'enable' or 'disable'.")
else:
    quiet = get_session_setting("quiet_mode", False)
    print(f"Quiet mode is {'on' if quiet else 'off'}")
