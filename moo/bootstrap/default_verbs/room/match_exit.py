#!moo verb match_exit --on $room

# pylint: disable=return-outside-function,undefined-variable,redefined-builtin

"""
This verb is used to determine if exit is the name of an exit leading out of the room. It performs a simple string
match on the names and aliases of the objects in the exits list stored as a property of the room. The intent here
is to allow for more sophisticated matching algorithms to be implemented. One might even go so far as implementing
a fuzzy matching scheme, to allow for player misspellings. If a successful match is made, this signifies that an
exit with the name exit leads from this room and is returned. If more than one match is found the
value AmbiguousObjectError is raised. If no match is found, the value NoSuchObject is raised.
"""

what = args[0].lower()
matches = []
exits = this.get_property("exits")
for exit in exits:
    if exit.is_named(what):
        matches.append(exit)
if len(matches) == 0:
    return None
elif len(matches) > 1:
    return matches
else:
    return matches[0]
