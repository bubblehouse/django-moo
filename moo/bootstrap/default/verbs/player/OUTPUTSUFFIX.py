#!moo verb OUTPUTSUFFIX --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Set global output suffix marker for machine parsing.

Usage:
    OUTPUTSUFFIX <marker>     Set global suffix to the specified marker string
    OUTPUTSUFFIX              Show current global suffix setting
    OUTPUTSUFFIX clear        Clear the global suffix

The OUTPUTSUFFIX command sets a marker string that will be emitted after all
output sent to the client, including asynchronous messages from other players.
This differs from SUFFIX, which only wraps the output of each command.

The global suffix is session-specific and will be cleared when you disconnect.

Example:
    OUTPUTPREFIX >>>
    OUTPUTSUFFIX <<<
    look
    >>>
    The Laboratory(#3)
    ...
    <<<

See also: OUTPUTPREFIX, PREFIX, SUFFIX, a11y
"""

from moo.sdk import get_session_setting, set_session_setting, context

# Get the marker from dobj string if provided
if context.parser.has_dobj_str():
    marker = context.parser.get_dobj_str()

    if marker.lower() == "clear":
        # Clear the global suffix
        set_session_setting("output_global_suffix", None)
        print("Global output suffix cleared")
    else:
        # Set the global suffix
        set_session_setting("output_global_suffix", marker)
        print(f"Global output suffix set to: {marker}")
else:
    # Show current setting
    suffix = get_session_setting("output_global_suffix")
    if suffix:
        print(f"Current global output suffix: {suffix}")
    else:
        print("No global output suffix set")
