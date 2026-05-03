#!moo verb OUTPUTPREFIX --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Set global output prefix marker for machine parsing.

Usage:
    OUTPUTPREFIX <marker>     Set global prefix to the specified marker string
    OUTPUTPREFIX              Show current global prefix setting
    OUTPUTPREFIX clear        Clear the global prefix

The OUTPUTPREFIX command sets a marker string that will be emitted before all
output sent to the client, including asynchronous messages from other players.
This differs from PREFIX, which only wraps the output of each command.

The global prefix is session-specific and will be cleared when you disconnect.

Example:
    OUTPUTPREFIX >>>
    OUTPUTSUFFIX <<<
    look
    >>>
    The Laboratory(#3)
    ...
    <<<

See also: OUTPUTSUFFIX, PREFIX, SUFFIX, a11y
"""

from moo.sdk import get_session_setting, set_session_setting, context

# Get the marker from dobj string if provided
if context.parser.has_dobj_str():
    marker = context.parser.get_dobj_str()

    if marker.lower() == "clear":
        # Clear the global prefix
        set_session_setting("output_global_prefix", None)
        print("Global output prefix cleared")
    else:
        # Set the global prefix
        set_session_setting("output_global_prefix", marker)
        print(f"Global output prefix set to: {marker}")
else:
    # Show current setting
    prefix = get_session_setting("output_global_prefix")
    if prefix:
        print(f"Current global output prefix: {prefix}")
    else:
        print("No global output prefix set")
