#!moo verb look --on $exit --dspec none --ispec through:any

# pylint: disable=return-outside-function,undefined-variable,redefined-builtin

from moo.core import context, lookup

door_description = context.parser.get_pobj_str("through")
exit = this

obj = exit.get_property("dest")
if not obj:
    print(f"There is no door called {door_description} here.")
    return

obj.look_self()
