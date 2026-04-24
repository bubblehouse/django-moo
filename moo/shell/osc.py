# -*- coding: utf-8 -*-
"""
OSC (Operating System Command) escape sequences for shell output.

OSC 133 (Semantic Shell Integration) lets screen readers and modern
terminals navigate command-by-command instead of line-by-line. The four
markers bracket each interactive cycle: prompt start, command start,
output start, and command end with an exit status.
"""

OSC_133_PROMPT_START = "\033]133;A\007"
OSC_133_COMMAND_START = "\033]133;B\007"
OSC_133_OUTPUT_START = "\033]133;C\007"


def osc_133_command_end(exit_status: int = 0) -> str:
    return f"\033]133;D;{exit_status}\007"
