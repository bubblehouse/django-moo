#!moo verb add_exit --on $room

"""
This verb is used to add exit to the list of exits leading out of the room. This verb, and the :match_exit verb provide
the interface to the room exits list. The way in which exits are stored, removed and matched has been separated from
the interface so that different implementations of the exits concept can be used in different sub classes of the $room
class.
"""
