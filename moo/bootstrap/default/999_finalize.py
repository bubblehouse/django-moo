# pylint: disable=undefined-variable
# Grant derive to everyone on all standard system classes so any player can
# create instances via @create without needing wizard privileges.
derive_perm = Permission.objects.get(name="derive")
for _cls in [root, thing, rooms, exits, player, programmers, furniture, containers, notes, letters]:
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
sys.gender_utils.set(player, "plural")
sys.set_property("gripe_recipients", [wizard])
