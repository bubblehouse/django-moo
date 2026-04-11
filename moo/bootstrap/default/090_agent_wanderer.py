# pylint: disable=undefined-variable
# The Wanderer — autonomous world explorer (timer-based, runs indefinitely)
# Cartographer ($programmers): surveys rooms, exercises @who/@whereis/@rooms/@audit
cartographer_obj, _ = bootstrap.get_or_create_object("Cartographer", unique_name=True, parents=[programmers])
cartographer_obj.owner = cartographer_obj
cartographer_obj.set_property("home", lab)
cartographer_obj.save()
cartographer_user, cartographer_created = User.objects.get_or_create(username="cartographer")
if cartographer_created:
    cartographer_user.set_password("Hc9vD2kRsM7p")
    cartographer_user.save()
Player.objects.get_or_create(user=cartographer_user, defaults=dict(avatar=cartographer_obj))
