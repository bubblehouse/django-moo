#!moo verb insert put --on $container --dspec any --ispec in:this --ispec on:this

# pylint: disable=return-outside-function,undefined-variable

"""
Put ``object`` into the container. The container is first checked to verify that it is open, if not an error message is printed.

For example, if you have a container named ``pipe`` and an object named ``tobacco``, you could enter::

    put tobacco in pipe

If pipe is open, then tobacco will be put into the pipe. If you look at pipe you should see::

    pipe
    Contents:
        tobacco
"""

from moo.sdk import context, UsageError

if not args:
    if not (context.parser.has_pobj_str("in") or context.parser.has_pobj_str("on")):
        raise UsageError(f"Usage: {verb_name} <object> in/on {this.name}")

obj = args[0] if args else context.parser.get_dobj()

if not this.is_open():
    print(f"{this.title()} is closed.")
    return

obj.moveto(this)

chosen_prep = "in" if "in" in context.parser.prepositions else "on"
print(f"You placed {obj.name} {chosen_prep} {this.name}")
