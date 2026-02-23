#!moo verb get take remove --on $container --dspec any --ispec from:this

# pylint: disable=return-outside-function,undefined-variable

"""
This does the opposite of the put/insert/drop commands. To remove the `tobacco` from the `pipe` you would enter:

    remove tobacco from pipe

When you look at pipe now you should see:

    pipe
    It is empty.
"""

from moo.core import api

object = args[0] if args else api.parser.get_dobj()
subject = api.parser.get_pobj("from") if api.parser.has_pobj("from") else api.player.location

if not this.is_open():
    print(f"{this.title()} is closed.")
    return

if object.location != this:
    print(f"{object.name} is not in {this.name}.")
    return

this.move_to(subject)
print(f"You took {object.name} from {this.name}")
