#!moo verb show_compass --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Overridable hook (spec 200, item A): whether ``look_self`` draws the compass
grid for this room.  Default True; a room that renders its own navigation can
return False.
"""

return True
