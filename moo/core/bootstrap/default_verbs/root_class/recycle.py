#!moo verb recycle --on "Root Class"

"""
This verb contains no code for the $root class. It is called by the obj.delete() primitive just before an object is
removed. This is useful to make sure that deleting objects does not leave the database in a strange state. For
example, the $exit class uses the `recycle` verb to remove the exit from the the entrance and exit lists of its
destination and source rooms.

By default, the `recycle` verb on $root does nothing.
"""

pass  # pylint: disable=unnecessary-pass  # type: ignore
