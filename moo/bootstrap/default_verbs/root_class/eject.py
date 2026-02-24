#!moo verb eject --on $root_class

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to remove `something` from the contents of an object. The owner of an object, or a wizard, can use
this verb to eject a victim from inside the object. The victim is sent to `None`, for most objects, or to
`$player_start` if the victim is a player.
"""

something = args[0]
if this.contains(something):
    if something.is_player():
        something.moveto(_.player_start)
    else:
        something.moveto(None)
else:
    print(f"{this.name} does not contain {something.name}.")
