#!moo verb remove_entrance --on $room

"""
This verb performs the opposite function to the `add_entrance` verb. It removes `entrance` from the room's list of
entrances. If it is not possible to remove `entrance` from the room's entrance list (normally because the object
that invoked the verb does not have the required permission) then the verb returns `False`. Otherwise, a successful
addition returns `True`.
"""
