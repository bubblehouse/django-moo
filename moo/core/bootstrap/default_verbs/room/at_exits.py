#!moo verb @exits --on $room

"""
This verb is a player command used to print a list of the exits in a room. It can only be used by the owner of the
room. The verb simply runs through the list of defined exits, stored in the property exits, and prints the exit name,
object reference number, destination name, and exit aliases.
"""
