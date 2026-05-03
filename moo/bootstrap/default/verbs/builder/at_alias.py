#!moo verb @alias add --on $builder --dspec any --ispec as:any

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

from moo.sdk import context, NoSuchObjectError

# Prefer objects visible in the current room or inventory over a global lookup.
# Fall back to global only for #N references or names not in local scope.
dobj_str = context.parser.get_dobj_str()
try:
    obj = context.player.location.match_object(dobj_str)
except NoSuchObjectError:
    obj = context.parser.get_dobj(lookup=True)

# Get the alias string
alias = context.parser.get_pobj_str("as")

# Add the alias - permissions are checked by the object model
if obj.add_alias(alias):
    print(f"[yellow]Added alias '{alias}' to {obj}[/yellow]")
else:
    print(f"[red]That alias '{alias}' is already set on {obj}.[/red]")
