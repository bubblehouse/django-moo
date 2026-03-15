#!moo verb add_entrance --on $room

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

"""
Add an entrance similarly to the :add_exit verb, but for $exit objects that lead into the room. If we
imagine an $exit object as a flexible tube connecting two rooms, then the concept of specifying both ends of the tube
seems natural. It is not usual to search the entrance list for a match, as you would with the exit list, but the
concept of an entrance is included to cover unexpected cases.

If it is not possible to add entrance to the room's entrance list (normally because the object that invoked the verb
does not have the required permission) then the verb returns ``0``. Otherwise, a successful addition returns ``1``.
"""

from moo.sdk import NoSuchPropertyError

entrance = args[0]

try:
    entrances = this.get_property("entrances")
except NoSuchPropertyError:
    entrances = []

entrances.append(entrance)
this.set_property("entrances", entrances)

return True
