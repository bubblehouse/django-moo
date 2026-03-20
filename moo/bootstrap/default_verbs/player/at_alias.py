#!moo verb @alias add --on $player --dspec any --ispec as:any

# pylint: disable=return-outside-function,undefined-variable

"""
Add an alias to an object.

Usage:
    @alias <object> as "<alias>"
    @alias #N as "alias"

The object can be specified by name (quoted if it contains spaces) or by
object ID (#N). Multiple aliases can be added to the same object by running
the command multiple times.

Examples:
    @alias "pool table" as "table"
    @alias #45 as "stool"
    @alias jukebox as "juke"

Permissions are enforced by the object model - you can only add aliases to
objects you own or have appropriate permissions for.
"""

from moo.sdk import context

# Get the target object (supports both names and #N IDs)
obj = context.parser.get_dobj(lookup=True)

# Get the alias string
alias = context.parser.get_pobj_str("as")

# Add the alias - permissions are checked by the object model
obj.add_alias(alias)

print(f"[yellow]Added alias '{alias}' to {obj}[/yellow]")
