# pylint: disable=undefined-variable
# The Neighbours — autonomous social-testing agents (timer-based, run simultaneously)
# Gossip ($player): Mrs. Helen Lovejoy; emotes, whispers, exercises social output
gossip_obj, _ = bootstrap.get_or_create_object("Gossip", unique_name=True, parents=[player])
gossip_obj.owner = gossip_obj
gossip_obj.set_property("home", neighborhood)
gossip_obj.save()
gossip_user, gossip_created = User.objects.get_or_create(username="gossip")
if gossip_created:
    gossip_user.set_password("Lk4tN7wCqX1e")
    gossip_user.save()
Player.objects.get_or_create(user=gossip_user, defaults=dict(avatar=gossip_obj))

# Prude ($player): Mrs. Agnes Skinner; gag/ungag/paranoid cycles, social filtering
prude_obj, _ = bootstrap.get_or_create_object("Prude", unique_name=True, parents=[player])
prude_obj.owner = prude_obj
prude_obj.set_property("home", neighborhood)
prude_obj.save()
prude_user, prude_created = User.objects.get_or_create(username="prude")
if prude_created:
    prude_user.set_password("Fy8eP5rTbW3m")
    prude_user.save()
Player.objects.get_or_create(user=prude_user, defaults=dict(avatar=prude_obj))
