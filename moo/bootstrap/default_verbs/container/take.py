#!moo verb get take remove --on $container --dspec any --ispec from:this

# pylint: disable=return-outside-function,undefined-variable

"""
This does the opposite of the put/insert/drop commands. To remove the `tobacco` from the `pipe` you would enter:

    remove tobacco from pipe

When you look at pipe now you should see:

    pipe
    It is empty.
"""

from moo.core import context

if args:
    obj = args[0]
    name = obj.title()
else:
    name = context.parser.get_dobj_str()
    obj = this.find(name).first()

if not this.is_open():
    print(f"{this.title()} is closed.")
    return

if not obj or obj.location != this:
    print(f"{name} is not in {this.title()}.")
    return

obj.moveto(context.player)
print(f"You took {name} from {this.title()}")
