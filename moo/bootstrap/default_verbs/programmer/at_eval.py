#!moo verb @eval --on $programmer --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Evaluate arbitrary Python code in the RestrictedPython sandbox.

Usage:
    @eval "<python-code>"

The code must be enclosed in quotes to avoid parser interference.

Examples:
    @eval "1 + 1"
    @eval "[x**2 for x in range(10)]"
    @eval "from moo.sdk import lookup; lookup('$wizard')"
    @eval "context.player.location.contents.all()"

The code runs with the same sandbox restrictions as verb code, with
standard verb variables (this, _, context) automatically available.
"""

from moo.sdk import moo_eval, context, set_task_perms

# Get the dobj string (which should be the quoted code)
code_to_eval = context.parser.get_dobj_str()

with set_task_perms(context.player):
    # Execute the code with error handling
    try:
        result = moo_eval(code_to_eval)
        # Print the result (REPL-like behavior)
        if result is not None:
            print(repr(result))
    except Exception as e:
        # Just stringify - will include exception type automatically
        print(f"Error: {e}")
