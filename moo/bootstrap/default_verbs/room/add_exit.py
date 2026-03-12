#!moo verb add_exit --on $room

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

"""
This verb is used to add exit to the list of exits leading out of the room. This verb, and the :match_exit verb provide
the interface to the room exits list. The way in which exits are stored, removed and matched has been separated from
the interface so that different implementations of the exits concept can be used in different sub classes of the $room
class.
"""

from moo.core import PropertyDoesNotExist

exit_obj = args[0]

try:
    exits = this.get_property("exits")
except PropertyDoesNotExist:
    exits = []

exits.append(exit_obj)
this.set_property("exits", exits)

return True
