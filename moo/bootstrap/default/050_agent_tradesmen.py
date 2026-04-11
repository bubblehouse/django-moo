# pylint: disable=undefined-variable
# The Tradesmen — autonomous builder agents
# Mason ($player): digs rooms and wires exits
mason_obj, _ = bootstrap.get_or_create_object("Mason", unique_name=True, parents=[player])
mason_obj.owner = mason_obj
mason_obj.set_property("home", agency)
mason_obj.save()
mason_user, mason_created = User.objects.get_or_create(username="mason")
if mason_created:
    mason_user.set_password("Mxq7vB2nKpL4")
    mason_user.save()
Player.objects.get_or_create(user=mason_user, defaults=dict(avatar=mason_obj))

# Tinker ($programmer): writes verbs for interactive objects and secret exits
tinker_obj, _ = bootstrap.get_or_create_object("Tinker", unique_name=True, parents=[programmers])
tinker_obj.owner = tinker_obj
tinker_obj.set_property("home", agency)
tinker_obj.save()
tinker_user, tinker_created = User.objects.get_or_create(username="tinker")
if tinker_created:
    tinker_user.set_password("Pw9cX3mZrT6y")
    tinker_user.save()
Player.objects.get_or_create(user=tinker_user, defaults=dict(avatar=tinker_obj))

# Joiner ($player): creates furniture and containers
joiner_obj, _ = bootstrap.get_or_create_object("Joiner", unique_name=True, parents=[player])
joiner_obj.owner = joiner_obj
joiner_obj.set_property("home", agency)
joiner_obj.save()
joiner_user, joiner_created = User.objects.get_or_create(username="joiner")
if joiner_created:
    joiner_user.set_password("Hn4kD8sQvY2f")
    joiner_user.save()
Player.objects.get_or_create(user=joiner_user, defaults=dict(avatar=joiner_obj))

# Harbinger ($programmer): creates NPCs, uses @eval for random roll and tell verb
harbinger_obj, _ = bootstrap.get_or_create_object("Harbinger", unique_name=True, parents=[programmers])
harbinger_obj.owner = harbinger_obj
harbinger_obj.set_property("home", agency)
harbinger_obj.save()
harbinger_user, harbinger_created = User.objects.get_or_create(username="harbinger")
if harbinger_created:
    harbinger_user.set_password("Bt6wF5jRcU3e")
    harbinger_user.save()
Player.objects.get_or_create(user=harbinger_user, defaults=dict(avatar=harbinger_obj))

# Stocker ($programmer): consumable items, dispensing objects, and multi-use props
stocker_obj, _ = bootstrap.get_or_create_object("Stocker", unique_name=True, parents=[programmers])
stocker_obj.owner = stocker_obj
stocker_obj.set_property("home", agency)
stocker_obj.save()
stocker_user, stocker_created = User.objects.get_or_create(username="stocker")
if stocker_created:
    stocker_user.set_password("Vn5sL9eJwA7k")
    stocker_user.save()
Player.objects.get_or_create(user=stocker_user, defaults=dict(avatar=stocker_obj))

# Foreman ($player): orchestrates token chain, detects stalls, loops automatically
foreman_obj, _ = bootstrap.get_or_create_object("Foreman", unique_name=True, parents=[player])
foreman_obj.owner = foreman_obj
foreman_obj.set_property("home", agency)
foreman_obj.save()
foreman_user, foreman_created = User.objects.get_or_create(username="foreman")
if foreman_created:
    foreman_user.set_password("Jk2mR7nXpW5q")
    foreman_user.save()
Player.objects.get_or_create(user=foreman_user, defaults=dict(avatar=foreman_obj))
