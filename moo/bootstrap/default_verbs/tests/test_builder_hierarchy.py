import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_builder_is_system_property(t_init: Object, t_wizard: Object):
    system = lookup(1)
    builder = system.get_property("builder")
    assert builder is not None
    assert builder.name == "Generic Builder"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_programmer_inherits_from_builder(t_init: Object, t_wizard: Object):
    system = lookup(1)
    programmer = system.get_property("programmer")
    builder = system.get_property("builder")
    assert programmer.parents.filter(pk=builder.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_builder_inherits_from_player(t_init: Object, t_wizard: Object):
    system = lookup(1)
    builder = system.get_property("builder")
    player = system.get_property("player")
    assert builder.parents.filter(pk=player.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_wizard_inherits_builder_transitively(t_init: Object, t_wizard: Object):
    """Wizard -> Programmer -> Builder -> Player, so wizard sees all builder verbs."""
    system = lookup(1)
    builder = system.get_property("builder")
    assert t_wizard.has_verb("@set")
    assert t_wizard.has_verb("@create")
    assert t_wizard.has_verb("@dig")
    assert builder.get_verb("@set") is not None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_builder_verbs_on_builder_not_player(t_init: Object, t_wizard: Object):
    """Moved verbs should be registered directly on $builder, and gone from $player."""
    from moo.core.exceptions import NoSuchVerbError

    system = lookup(1)
    builder = system.get_property("builder")
    player = system.get_property("player")

    builder_verbs = [
        "@create",
        "@dig",
        "@burrow",
        "@describe",
        "@rename",
        "@alias",
        "@recycle",
        "@lock",
        "@unlock",
        "@obvious",
        "@nonobvious",
        "@move",
        "@add-key",
        "@remove-key",
        "@keys",
        "@eject",
        "@set",
        "@divine",
        "@rooms",
        "@realm",
        "teleport",
        "@survey",
    ]
    for name in builder_verbs:
        # recurse=False: must be defined directly on $builder, not inherited
        assert builder.get_verb(name, recurse=False) is not None, f"{name} missing directly on $builder"
        with pytest.raises(NoSuchVerbError):
            player.get_verb(name, recurse=False)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_plain_player_cannot_build(t_init: Object, t_wizard: Object):
    """A $player avatar (no builder inheritance) cannot run builder verbs."""
    system = lookup(1)
    avatar = create("Citizen", parents=[system.player], location=t_wizard.location)
    assert not avatar.has_verb("@create")
    assert not avatar.has_verb("@dig")
    assert not avatar.has_verb("@set")
    assert not avatar.has_verb("@lock")
    assert avatar.has_verb("inventory")
    assert avatar.has_verb("take")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_builder_avatar_has_builder_verbs_not_eval(t_init: Object, t_wizard: Object):
    """A $builder avatar has building verbs but not @eval/@edit/@version (programmer/wizard-only)."""
    system = lookup(1)
    builder = system.get_property("builder")
    avatar = create("Tradesman", parents=[builder], location=t_wizard.location)
    for verb in ("@create", "@dig", "@set", "@lock", "@divine", "teleport", "@survey", "@rooms"):
        assert avatar.has_verb(verb), f"$builder avatar should have {verb}"
    for verb in ("@eval", "@edit", "@version"):
        assert not avatar.has_verb(verb), f"$builder avatar should NOT have {verb}"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tradesmen_agents_are_builders(t_init: Object, t_wizard: Object):
    """Mason, Joiner, Warden, Quartermaster are parented to $builder."""
    system = lookup(1)
    builder = system.get_property("builder")
    for name in ("Mason", "Joiner", "Warden", "Quartermaster"):
        agent = Object.objects.get(name=name)
        assert agent.parents.filter(pk=builder.pk).exists(), f"{name} not parented to $builder"
