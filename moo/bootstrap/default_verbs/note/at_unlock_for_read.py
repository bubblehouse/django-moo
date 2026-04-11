#!moo verb @unlock_for_read unlock_for_read --on $note --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Remove the lock set by @lock_for_read. It can only be run by the owner of the note.
"""

this.set_property("read_key", None)
print(f"Lock removed from {this.name}.")
