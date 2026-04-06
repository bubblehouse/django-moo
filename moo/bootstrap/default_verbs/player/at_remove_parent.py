#!moo verb @remove_parent --on $player --dspec any --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
Remove a parent class from an object. The direct object is the parent to remove;
the indirect object (after "from") is the object to modify.

Usage: @remove_parent "$furniture" from #N
       @remove_parent "$container" from "oak desk"

Requires write permission on the object and derive permission on the parent.
"""

from moo.sdk import context, lookup

parser = context.parser
parent = parser.get_dobj(lookup=True)
obj = parser.get_pobj("from", lookup=True)
obj.remove_parent(parent)
print(f"Removed {parent} as a parent of {obj}.")
