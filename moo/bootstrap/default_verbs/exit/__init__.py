"""
The `$exit` class is the other type of object used to construct the fabric of the virtual world. You can imagine an
exit to be a flexible tube connecting two `$room` objects. Each `$exit` object goes in one direction only. It leads
from a source object to a destination object. Note that it takes no virtual time to traverse an exit. When an object
moves through an exit, it moves from one room to another instantaneously.

The verbs defined for the `$exit` class are fairly simple and obvious. Several messages are defined as properties on an
`$exit`. These are pronoun substituted and printed when the `$exit` is invoked, under various conditions.
"""
