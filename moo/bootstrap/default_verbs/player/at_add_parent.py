#!moo verb @add_parent --on $player --dspec any --ispec to:any

# pylint: disable=return-outside-function,undefined-variable

"""
Add a parent class to an object. The direct object is the object to modify;
the indirect object (after "to") is the parent class to add.

Usage: @add_parent #N to "$furniture"
       @add_parent "oak desk" to "$container"

Requires write permission on the object and derive permission on the parent.
"""

from moo.sdk import context, lookup

parser = context.parser
obj = parser.get_dobj()
parent = parser.get_pobj("to", lookup=True)
obj.add_parent(parent)
print(f"Added {parent} as a parent of {obj}.")
