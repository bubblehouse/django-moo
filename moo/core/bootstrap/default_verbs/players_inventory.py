#!moo verb i*nventory --on $player

"""
This verb is used to tell a player what s/he has in his/her pockets.
"""

if this.contents.count() > 0:
  this.tell("You are carrying:")
  for thing in this.contents.all():
    this.tell(thing.title())
else:
  this.tell("You are empty-handed.")
