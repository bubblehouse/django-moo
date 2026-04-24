#!moo verb a11y @accessibility --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Manage accessibility-related session settings.

Usage:
    a11y                    Show all current settings
    a11y <setting> on       Turn a setting on
    a11y <setting> off      Turn a setting off

Settings:
    osc133     OSC 133 prompt/command/output markers for screen readers
               and modern terminals (default: on)
    prefixes   Prepend [ERROR] / [WARN] / [INFO] textual tags to colored
               output so meaning survives ANSI-color stripping
               (default: off)
    quiet      Suppress Rich color codes and use a bare "$" prompt; for
               machine-readable output (default: off; replaces the
               standalone QUIET verb)

Settings are session-specific and cleared on disconnect. The verb is
also reachable as @accessibility.

Examples:
    a11y prefixes on
    a11y osc133 off
    @accessibility quiet on
"""

from moo.sdk import get_session_setting, set_session_setting, context

SETTINGS = {
    "osc133": ("osc133_mode", True),
    "prefixes": ("prefixes_mode", False),
    "quiet": ("quiet_mode", False),
}

# ``on`` and ``off`` are MOO prepositions, so ``a11y quiet on`` is parsed
# as verb=a11y, dobj="quiet" with no pobj — the trailing ``on`` is stripped
# by the parser because a preposition with no object is discarded. Read the
# setting and action from parser.words (the raw tokenised command) to
# survive that quirk.
parser = context.parser
words = [w.lower() for w in parser.words]

if len(words) < 2:
    print("Accessibility settings:")
    for setting_name, (setting_key, setting_default) in SETTINGS.items():
        state = "on" if get_session_setting(setting_key, setting_default) else "off"
        print(f"  {setting_name:<10} {state}")
else:
    setting = words[1]
    action = words[2] if len(words) >= 3 else None
    if setting not in SETTINGS:
        valid = ", ".join(SETTINGS.keys())
        print(f"Unknown setting: {setting!r}. Valid settings: {valid}")
    elif action not in ("on", "off"):
        print(f"Usage: a11y {setting} on|off")
    else:
        session_key = SETTINGS[setting][0]
        new_value = action == "on"
        set_session_setting(session_key, new_value)
        print(f"{setting} {action}")
