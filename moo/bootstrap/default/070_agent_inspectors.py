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

# Warden's master key: a persistent test key for keyed exit locking.
# Owned by Warden, starts in Warden's inventory. Lets Warden exercise
# `lock <dir> with #<key>` without having to create a new key each session.
warden_key, _ = bootstrap.get_or_create_object(
    "warden's master key", unique_name=True, parents=[thing], location=warden_obj
)
warden_key.owner = warden_obj
warden_key.save()
warden_key.set_property("description", "A heavy iron skeleton key, worn smooth from constant use.")
warden_key.add_alias("master key")

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

# Give each inspector a personal flashlight so they can work in dark rooms.
for _agent in (quartermaster_obj, warden_obj, archivist_obj):
    _flash, _ = bootstrap.get_or_create_object(
        f"{_agent.name}'s flashlight", unique_name=True, parents=[flashlight], location=_agent
    )
    _flash.owner = _agent
    _flash.save()
    _flash.add_alias("flashlight")
