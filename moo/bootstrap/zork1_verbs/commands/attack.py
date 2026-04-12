#!moo verb attack kill hit fight stab --on $player --dspec any
# pylint: disable=return-outside-function,undefined-variable
"""Attack a creature or object."""

from moo.sdk import context, NoSuchObjectError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't see that here.")
    return

if not _.zork_sdk.flag(obj, "hostile") and not _.zork_sdk.flag(obj, "fightable"):
    print(f"Attacking the {_.zork_sdk.desc(obj)} doesn't seem productive.")
    return

if obj.has_verb("attack_action"):
    obj.invoke_verb("attack_action")
else:
    print(f"You attack the {_.zork_sdk.desc(obj)}, but nothing happens.")
