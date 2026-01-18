#!moo verb match_exit --on $room

"""
This verb is used to determine if exit is the name of an exit leading out of the room. It performs a simple string
match on the names and aliases of the objects in the exits list stored as a property of the room. The intent here
is to allow for more sophisticated matching algorithms to be implemented. One might even go so far as implementing
a fuzzy matching scheme, to allow for player misspellings. If a successful match is made, this signifies that an
exit with the name exit leads from this room and is returned. If more than one match is found the
value $ambiguous_match is returned. If no match is found, the value $failed_match is returned.
"""
