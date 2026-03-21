"""
The `$furniture` class defines verbs and properties for objects that are fixed in place — chairs, couches, tables,
and similar items that cannot be picked up or moved. It is a subclass of `$thing` with two key differences:

1. The `moveto` verb is overridden to return `False`, making any attempt to take or move the object fail.
2. New `sit` and `stand` verbs allow players to sit on furniture and stand back up, tracked via a `seated_on`
   property on the player.

Message properties follow the same configurable `*_msg` pattern as `$thing`, using `pronoun_sub` format codes.
"""
