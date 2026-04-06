#!moo verb @add_parent --on $player --dspec any --ispec to:any

# pylint: disable=return-outside-function,undefined-variable

"""
Add a parent class to an object. The direct object is the parent to add;
the indirect object (after "to") is the object to modify.

Usage: @add_parent "$furniture" to #N
       @add_parent "$container" to "oak desk"

Requires write permission on the object and derive permission on the parent.
"""

from moo.sdk import context, lookup

parser = context.parser
parent = parser.get_dobj(lookup=True)
obj = parser.get_pobj("to", lookup=True)
obj.add_parent(parent)
print(f"Added {parent} as a parent of {obj}.")
