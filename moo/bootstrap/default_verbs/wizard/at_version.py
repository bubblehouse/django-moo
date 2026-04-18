#!moo verb @version @memory --on $wizard

# pylint: disable=return-outside-function,undefined-variable

"""
Display server version and memory information (wizard only).

Usage:
    @version    — show server version, Python version, and process ID
    @memory     — show current process memory usage (RSS)
"""

from moo.sdk import context, server_info

if not context.player.is_wizard():
    print("Permission denied.")
    return

info = server_info()
if verb_name == "@memory":
    if info["memory_mb"] is not None:
        print(f"Memory usage: {info['memory_mb']} MB (RSS)")
    else:
        print("Memory info unavailable on this platform.")
else:
    print(f"Version: {info['version']}")
    print(f"Python:  {info['python']}")
    print(f"PID:     {info['pid']}")
