# pylint: disable=undefined-variable
# Grant derive to everyone on all standard system classes so any player can
# create instances via @create without needing wizard privileges.
derive_perm = Permission.objects.get(name="derive")
for _cls in [
    root,
    thing,
    rooms,
    exits,
    player,
    builders,
    programmers,
    furniture,
    containers,
    notes,
    letters,
    bulletin_board,
    book,
    flashlight,
]:
    Access.objects.get_or_create(
        object=_cls,
        permission=derive_perm,
        type="group",
        group="everyone",
        rule="allow",
    )

# Remove the temporary bootstrap accept verbs — verb files provide the real ones.
if root.has_verb("accept"):
    root.get_verb("accept").delete()
if containers.has_verb("accept"):
    containers.get_verb("accept").delete()
bootstrap.load_verbs(repo, "moo.bootstrap.default_verbs", replace=True)

# TODO: REMOVE AFTER moo_init --sync HAS RUN ON ALL DEPLOYED DBs.
# One-shot cleanup of orphan Verb rows from verbs relocated from $player/$programmer
# to $builder. Verb.filename stores a resolved absolute path, so we match the old
# directory segment (e.g. "/player/at_create.py") to avoid nuking the new row under
# /builder/. Idempotent no-op on a fresh DB where those rows never existed.
from moo.core.models import Verb  # pylint: disable=wrong-import-position

_moved_from_player = [
    "at_create.py",
    "at_dig.py",
    "at_burrow.py",
    "at_describe.py",
    "at_rename.py",
    "at_alias.py",
    "at_recycle.py",
    "at_lock.py",
    "at_unlock.py",
    "at_obvious.py",
    "at_nonobvious.py",
    "at_move.py",
    "at_add_key.py",
    "at_remove_key.py",
    "at_keys.py",
    "at_eject.py",
    "at_divine.py",
    "at_rooms.py",
    "at_realm.py",
    "at_teleport.py",
    "at_survey.py",
    "at_version.py",
]
for _name in _moved_from_player:
    Verb.objects.filter(origin=player, filename__endswith=f"/player/{_name}").delete()
Verb.objects.filter(origin=programmers, filename__endswith="/programmer/at_set.py").delete()

sys.gender_utils.set(player, "plural")
sys.set_property("gripe_recipients", [wizard])
