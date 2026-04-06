#!moo verb @remove_parent --on $player --dspec any --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
Remove a parent class from an object. The direct object is the object to modify;
the indirect object (after "from") is the parent class to remove.

Usage: @remove_parent #N from "$furniture"
       @remove_parent "oak desk" from "$container"

Requires write permission on the object and derive permission on the parent.
"""

from moo.sdk import context, lookup

parser = context.parser
obj = parser.get_dobj()
parent = parser.get_pobj("from", lookup=True)
obj.remove_parent(parent)
print(f"Removed {parent} as a parent of {obj}.")
