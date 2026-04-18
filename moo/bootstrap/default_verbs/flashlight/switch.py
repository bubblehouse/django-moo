#!moo verb switch --on $flashlight --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Toggle the flashlight's ``alight`` state. Narrates the new state to the
caller and the room.
"""

from moo.sdk import context

current = bool(this.get_property("alight"))
new_state = not current
this.set_property("alight", new_state)

if new_state:
    print(f"You switch on the {this.title()}.")
    if context.player.location:
        context.player.location.announce_all_but(
            context.player, f"{context.player.title()} switches on the {this.title()}."
        )
else:
    print(f"You switch off the {this.title()}.")
    if context.player.location:
        context.player.location.announce_all_but(
            context.player, f"{context.player.title()} switches off the {this.title()}."
        )
