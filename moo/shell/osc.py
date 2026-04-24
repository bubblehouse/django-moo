# -*- coding: utf-8 -*-
"""
OSC 133 (Semantic Shell Integration) escape sequences.

The four markers bracket each interactive cycle: prompt start, command
start, output start, and command end with exit status. See
:doc:`/explanation/shell-internals` § "OSC 133 Semantic Shell Integration"
for how the prompt uses them.
"""

OSC_133_PROMPT_START = "\033]133;A\007"
OSC_133_COMMAND_START = "\033]133;B\007"
OSC_133_OUTPUT_START = "\033]133;C\007"


def osc_133_command_end(exit_status: int = 0) -> str:
    return f"\033]133;D;{exit_status}\007"
