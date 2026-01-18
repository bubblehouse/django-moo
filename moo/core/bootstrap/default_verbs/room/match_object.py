#!moo verb match_object --on $room

"""
This is the verb used to search the player's locale for an object that has the name or pseudonym name. This verb
handles mapping of me to the player object, here to the player's location as well as the use of #<number> to refer to a
particular object. If none of these cases match, the verb searches the room contents and the players contents (or
possessions) for a match. If a match is found, then the unique object number is returned. If name matches more than one
object, then $ambiguous_match is returned. If no match is found, then $failed_match is returned.

The verb :match_object is the one to use to map names of objects to object numbers, when referring to objects that the
player is able to see in his current location. This includes objects that the player might be carrying, but does not
include objects that are contained in other objects.
"""
