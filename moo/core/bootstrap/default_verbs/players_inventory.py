#!moo verb i*nventory --on $player

"""
This verb is used to tell a player what s/he has in his/her pockets.
"""

if this.contents:
  this.tell("You are carrying:")
  for thing in this.contents:
    this.tell(thing.title())
else:
  this.tell("You are empty-handed.")
