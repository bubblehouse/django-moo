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

# $builder and $programmer are capability rungs, not content classes. Anyone
# who can derive from one can add it to their own avatar and gain its verbs,
# so only wizards may grant them. Remove any grant an earlier sync made.
Access.objects.filter(
    object__in=[builders, programmers],
    permission=derive_perm,
    type="group",
    group="everyone",
    rule="allow",
).delete()

# Remove the temporary bootstrap accept verbs — verb files provide the real ones.
if root.has_verb("accept"):
    root.get_verb("accept").delete()
if containers.has_verb("accept"):
    containers.get_verb("accept").delete()
bootstrap.load_verbs(repo, "moo.bootstrap.default.verbs", replace=True)

sys.gender_utils.set(player, "plural")
sys.set_property("gripe_recipients", [wizard])
