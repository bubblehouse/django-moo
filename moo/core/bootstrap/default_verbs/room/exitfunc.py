#!moo verb exitfunc --on $room

"""
This verb is invoked by the LambdaMOO server when an object is moved out of a room, as part of the action of the `move`
primitive. The action defined for the `$room` class is to do nothing.

This verb, and the `enterfunc` verb, can be used for a variety of effects that need to take note of objects moving in
and out of rooms. For example, consider a torch object that casts light on its surroundings. When the torch is moved
out of a room, the light that is casts moves with it. This can be tackled using the room's `exitfunc`, which could check
if the object leaving is a torch, and if it is, the room could become dark. Similarly, when the torch enters a room,
the `enterfunc` can be used to detect this, and brighten the room accordingly.
"""

pass
