#!moo verb remove_exit --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This verb performs the opposite function to the `add_exit` verb. It removes `exit` from the room's list of exits. If it is
not possible to remove `exit` from the room's exit list (normally because the object that invoked the verb does not have
the required permission) then the verb returns `False`. Otherwise, a successful addition returns `True`.
"""

from moo.core import PropertyDoesNotExist

exit = args[0]

try:
    exits = this.get_property("exits")
except PropertyDoesNotExist:
    exits = []

exits.remove(exit)
this.set_property("exits", exits)

return True
