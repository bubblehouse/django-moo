#!moo verb moveto --on $furniture

# pylint: disable=return-outside-function,undefined-variable

"""
Override of `$thing.moveto`. Furniture is fixed in place and cannot be moved by players — taking,
dropping, giving, or teleporting all return `False`, which causes `$thing.take` to print the
`take_failed_msg` property.

Wizards are exempt: a wizard (or wizard-owned verb) can move furniture freely, which allows
`@create ... from "$furniture"` to place the new object into inventory, and `@move` to
relocate furniture between rooms during building.
"""

from moo.sdk import context

if context.player and context.player.is_wizard():
    return passthrough(args[0])

return False
