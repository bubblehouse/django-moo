#!moo verb accept --on $room

"""
This verb is used to control what objects are permitted to be placed inside other objects. If this verb returns
`False`, then the object where cannot be moved into this object. Conversely, if the verb returns a non-zero value, the
object is allowed to be placed inside this object. The verb is called by the server when it changes the `location`
property of an object.

The `$room` class definition provides for a flexible scheme using various different criteria, as shown in the following code:

what = args[0];
return this:is_unlocked_for(what) &&
       (this.free_entry ||
       what.owner == this.owner ||
       (typeof(this.residents) == LIST && what in this.residents));

Starting at the top of the conditional expression, we see the locking condition being checked. If the room lock
forbids this object to enter the room, then the :accept verb returns zero.

If this is not the case, then we consider the value of the `free_entry` property. If this is set to a non-zero
value, then the object is allowed to enter the room.

If the owner of an object is the owner of a room, the object is allowed to enter.

Finally, if a `residents` list is defined in the room, and the object is in the list, then it is allowed to enter.
This complex set of conditions shows how an arbitrary set of criteria can be applied to the movement of objects into other objects.
"""

# TODO: Implement room accept logic
thing = args[0]

return True
