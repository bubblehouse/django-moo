#!moo verb remove_exit --on $room

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

"""
Perform the opposite function to the `add_exit` verb. It removes `exit`` from the room``s list of exits. If it is
not possible to remove `exit`` from the room``s exit list (normally because the object that invoked the verb does not have
the required permission) then the verb returns `False`. Otherwise, a successful addition returns `True`.
"""

from moo.core import NoSuchPropertyError

exit_obj = args[0]

try:
    exits = this.get_property("exits")
except NoSuchPropertyError:
    exits = []

exits.remove(exit_obj)
this.set_property("exits", exits)

return True
