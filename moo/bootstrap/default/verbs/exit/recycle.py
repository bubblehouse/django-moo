#!moo verb recycle --on $exit

# pylint: disable=return-outside-function,undefined-variable

"""
Remove an exit tidily from the database. The exit is removed from the entrance and
exit lists of the destination and source rooms respectively, if the caller of this verb has permission to do so. This
is done using the `$room.remove_(entrance|exit)` verbs.
"""
