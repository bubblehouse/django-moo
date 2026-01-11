#!moo verb bless_for_entry --on $room

"""
This verb is called by an exit to allow an object special permission to enter a room. Two properties on the room store
thing and the task_id of the calling task. The idea behind blessed objects is to allow an object temporary permission
to enter. The permission is only granted if the request is made by an object that is an entrance into the room.

The idea here is that a normally inaccessible room can be entered providing you use an exit that leads into the room.
In addition, the task ID of the task that asked for the blessing is stored, so that there is no way an object can
become blessed, and then later gain entry to the room. The object being blessed is only allowed to enter once per
blessing. Once the object has moved into the room, it's blessed status is removed by resetting the blessed_object
property in the room to $nothing.
"""
