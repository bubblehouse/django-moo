#!moo verb @nonobvious --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""

Mark an object as non-obvious so it is hidden from room contents listings.
The caller must have write permission on the object.
"""

from moo.sdk import context

obj = context.parser.get_dobj()
context.player.is_allowed("write", obj, fatal=True)
obj.obvious = False
obj.save()
print(f"{obj.title()} is now non-obvious.")
