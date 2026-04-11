# pylint: disable=undefined-variable
# The Inspectors — autonomous verb-testing agents (token chain via Foreman)
# Quartermaster ($player): exercises container open/close/take/put/lock mechanics
quartermaster_obj, _ = bootstrap.get_or_create_object("Quartermaster", unique_name=True, parents=[player])
quartermaster_obj.owner = quartermaster_obj
quartermaster_obj.set_property("home", agency)
quartermaster_obj.save()
quartermaster_user, quartermaster_created = User.objects.get_or_create(username="quartermaster")
if quartermaster_created:
    quartermaster_user.set_password("Xp3nQ8vLmT2k")
    quartermaster_user.save()
Player.objects.get_or_create(user=quartermaster_user, defaults=dict(avatar=quartermaster_obj))

# Warden ($player): exercises exit locking, @lock/@unlock, key-based traversal
warden_obj, _ = bootstrap.get_or_create_object("Warden", unique_name=True, parents=[player])
warden_obj.owner = warden_obj
warden_obj.set_property("home", agency)
warden_obj.save()
warden_user, warden_created = User.objects.get_or_create(username="warden")
if warden_created:
    warden_user.set_password("Bz6wR4hNsY9j")
    warden_user.save()
Player.objects.get_or_create(user=warden_user, defaults=dict(avatar=warden_obj))

# Archivist ($player): exercises note/letter create, read, lock, erase, burn
archivist_obj, _ = bootstrap.get_or_create_object("Archivist", unique_name=True, parents=[player])
archivist_obj.owner = archivist_obj
archivist_obj.set_property("home", agency)
archivist_obj.save()
archivist_user, archivist_created = User.objects.get_or_create(username="archivist")
if archivist_created:
    archivist_user.set_password("Wr7mK5pDcF3n")
    archivist_user.save()
Player.objects.get_or_create(user=archivist_user, defaults=dict(avatar=archivist_obj))

# Tailor ($player): exercises @gender, pronoun substitution, @messages, @check
tailor_obj, _ = bootstrap.get_or_create_object("Tailor", unique_name=True, parents=[player])
tailor_obj.owner = tailor_obj
tailor_obj.set_property("home", agency)
tailor_obj.save()
tailor_user, tailor_created = User.objects.get_or_create(username="tailor")
if tailor_created:
    tailor_user.set_password("Gv2sM9xJnH6q")
    tailor_user.save()
Player.objects.get_or_create(user=tailor_user, defaults=dict(avatar=tailor_obj))
