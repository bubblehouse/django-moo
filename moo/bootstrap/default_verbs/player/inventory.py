#!moo verb i*nventory --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to tell a player what s/he has in his/her pockets.
"""

contents = list(this.contents.all())
if contents:
    this.tell("You are carrying:")
    for thing in contents:
        this.tell(thing.title())
else:
    this.tell("You are empty-handed.")
