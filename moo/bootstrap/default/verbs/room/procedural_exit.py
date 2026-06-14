#!moo verb procedural_exit --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Overridable hook (spec 200, item D): resolve an exit by a function over the
room's position instead of a stored ``$exit`` object.

Default returns ``None`` (rooms use stored exits as before).  A lattice/overworld
room overrides this to compute adjacency on the fly and return an ``$exit``
object (with ``source``/``dest`` set) for the given direction — the movement
verbs then drive it through the standard ``exit.invoke`` → ``move`` path, so a
computed exit produces the same leave/arrive messaging and ``Room.Info`` GMCP as
a stored one.  Returning ``None`` means "no exit that way".

Called as ``room.procedural_exit(direction)``.
"""

return None
