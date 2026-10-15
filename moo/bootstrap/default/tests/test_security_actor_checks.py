"""
Actor checks in Wizard-owned command and helper verbs.

Every ``default`` verb is owned by the Wizard, so ``context.caller`` inside it
is the Wizard and every model-level permission check passes. A command verb
must therefore check ``context.player`` before it changes a target, and a
helper verb that changes ``this`` must check ``caller_perms()``, the owner of
the code that called it. Without these checks, a non-wizard could rewrite any
object, and a self-made ``$programmer`` could rewrite a Wizard-owned verb and
run code as the Wizard.
"""

import pytest

from moo.core import code, parse
from moo.core.models import Object, Verb
from moo.core.models.acl import Access
from moo.sdk import create, lookup


def setup_world(t_wizard, programmer=False):
    """
    Return a non-wizard avatar standing in a Wizard-owned room.

    The room holds a Wizard-owned thing, container, note, and exit. The
    avatar also owns a room and a thing of its own.
    """
    sys = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None):
        hall = create("Wizard Hall", parents=[sys.room], location=None)
        statue = create("Wizard Statue", parents=[sys.thing], location=hall)
        chest = create("Wizard Chest", parents=[sys.container], location=hall)
        memo = create("Wizard Memo", parents=[sys.note], location=hall)
        vault = create("Wizard Vault", parents=[sys.room], location=None)
        door = create("vault door", parents=[sys.exit], location=None)
        door.add_alias("east")
        door.set_property("source", hall)
        door.set_property("dest", vault)
        hall.add_exit(door)
        vault.add_entrance(door)
        p = lookup("Player")
        p.parents.add(sys.builder)
        if programmer:
            p.parents.add(sys.programmer)
        den = create("Player Den", parents=[sys.room], location=None)
        trinket = create("Player Trinket", parents=[sys.thing], location=hall)
        for owned in (den, trinket):
            owned.owner = p
            owned.save()
        p.location = hall
        p.save()
    return {
        "player": p,
        "hall": hall,
        "statue": statue,
        "chest": chest,
        "memo": memo,
        "vault": vault,
        "door": door,
        "den": den,
        "trinket": trinket,
    }


def run(avatar, line):
    """Run one command as `avatar` and return its printed output."""
    out = []
    with code.ContextManager(avatar, out.append) as ctx:
        parse.interpret(ctx, line)
    return out


def denied(avatar, line):
    """Run one command as `avatar` and assert that it raises ``PermissionError``."""
    with pytest.raises(PermissionError):
        run(avatar, line)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_player_cannot_self_promote_to_programmer(t_init: Object, t_wizard: Object):
    """
    ``@add_parent "$programmer" to me`` used to succeed for any player: the
    avatar owns itself (``transmute``) and ``999_finalize`` granted everyone
    ``derive`` on ``$programmer``. The capability rungs no longer carry that grant.
    """
    sys = lookup(1)
    w = setup_world(t_wizard)
    p = w["player"]
    for rung in ("$programmer", "$builder"):
        with code.ContextManager(t_wizard, lambda _: None):
            p.parents.remove(sys.builder)
        denied(p, f'@add_parent "{rung}" to me')
    assert not p.parents.filter(pk__in=[sys.programmer.pk, sys.builder.pk]).exists()
    # The same promotion through raw ORM access in the player's own task.
    with code.ContextManager(p, lambda _: None):
        with pytest.raises(PermissionError):
            p.parents.add(sys.programmer)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rung_derive_grants_are_removed(t_init: Object, t_wizard: Object):
    """Content classes stay derivable by everyone; the rung classes do not."""
    sys = lookup(1)
    grants = Access.objects.filter(permission__name="derive", group="everyone", rule="allow")
    assert not grants.filter(object__in=[sys.builder, sys.programmer]).exists()
    assert grants.filter(object=sys.thing).exists()
    assert grants.filter(object=sys.container).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_add_parent_on_own_object_still_works(t_init: Object, t_wizard: Object):
    """A player can still mix a content class into an object they own."""
    sys = lookup(1)
    w = setup_world(t_wizard)
    run(w["player"], f'@add_parent "$container" to #{w["trinket"].pk}')
    assert w["trinket"].parents.filter(pk=sys.container.pk).exists()
    denied(w["player"], f'@add_parent "$container" to #{w["statue"].pk}')


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_programmer_cannot_edit_wizard_verb(t_init: Object, t_wizard: Object):
    """
    A Wizard-owned verb keeps its owner when its code changes, so it would run
    the new code as the Wizard. ``@edit`` now needs ``write`` on the verb.
    """
    w = setup_world(t_wizard, programmer=True)
    with code.ContextManager(t_wizard, lambda _: None):
        w["statue"].add_verb("zap", code="return 1")
    verb = Verb.objects.get(origin=w["statue"], names__name="zap")
    denied(w["player"], f'@edit verb zap on #{w["statue"].pk} with "return 2"')
    denied(w["player"], f'@edit property description on #{w["statue"].pk} with "x"')
    denied(w["player"], f'@edit verb newverb on #{w["statue"].pk} with "return 3"')
    verb.refresh_from_db()
    assert verb.code == "return 1"
    with pytest.raises(Verb.DoesNotExist):
        Verb.objects.get(origin=w["statue"], names__name="newverb")
    # The editor callback is a verb anyone can call; it checks too.
    out = run(w["player"], f"@eval \"context.player.edit_callback('return 4', {verb.pk}, 'verb')\"")
    assert any("not allowed" in line for line in out)
    verb.refresh_from_db()
    assert verb.code == "return 1"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_programmer_can_edit_own_verb(t_init: Object, t_wizard: Object):
    """``@edit`` still works on the programmer's own objects."""
    w = setup_world(t_wizard, programmer=True)
    run(w["player"], f'@edit verb poke on #{w["trinket"].pk} with "return 5"')
    verb = Verb.objects.get(origin=w["trinket"], names__name="poke")
    run(w["player"], f'@edit verb poke on #{w["trinket"].pk} with "return 6"')
    verb.refresh_from_db()
    assert verb.code == "return 6"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_move_needs_move_permission(t_init: Object, t_wizard: Object):
    """``moveto`` runs as the moved object's owner, so ``@move`` checks the player first."""
    w = setup_world(t_wizard)
    lab = lookup("The Laboratory")
    denied(w["player"], f"@move #{w['statue'].pk} to #{lab.pk}")
    w["statue"].refresh_from_db()
    assert w["statue"].location == w["hall"]
    run(w["player"], f"@move #{w['trinket'].pk} to #{lab.pk}")
    w["trinket"].refresh_from_db()
    assert w["trinket"].location == lab
    run(w["player"], f"@move me to #{w['den'].pk}")
    w["player"].refresh_from_db()
    assert w["player"].location == w["den"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_needs_write(t_init: Object, t_wizard: Object):
    """``describe`` writes as the Wizard, so ``@describe`` checks the player first."""
    w = setup_world(t_wizard)
    denied(w["player"], f'@describe #{w["hall"].pk} as "hacked"')
    run(w["player"], f'@describe #{w["trinket"].pk} as "shiny"')
    with code.ContextManager(t_wizard, lambda _: None):
        assert w["hall"].get_property("description") != "hacked"
        assert w["trinket"].get_property("description") == "shiny"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dig_needs_write_on_the_room(t_init: Object, t_wizard: Object):
    """``add_exit`` writes as the Wizard; the dig commands check the room before creating anything."""
    w = setup_world(t_wizard)
    p = w["player"]
    with code.ContextManager(t_wizard, lambda _: None):
        quota = p.get_property("ownership_quota")
    denied(p, "@dig north to Secret Den")
    denied(p, "@burrow north to Secret Den")
    with code.ContextManager(t_wizard, lambda _: None):
        assert p.get_property("ownership_quota") == quota
        assert w["hall"].get_property("exits") == [w["door"]]
    run(p, f"@move me to #{w['den'].pk}")
    denied(p, f"@tunnel west to #{w['vault'].pk}")
    run(p, "@dig north to Den Annex")
    with code.ContextManager(t_wizard, lambda _: None):
        assert len(w["den"].get_property("exits")) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
@pytest.mark.parametrize(
    "template",
    [
        '@alias #{pk} as "rock"',
        "@lock #{pk} with me",
        "@unlock #{pk}",
        "@recycle #{pk}",
        "@destroy #{pk}",
    ],
)
def test_builder_commands_need_write(t_init: Object, t_wizard: Object, template):
    """Each command changes its target as the Wizard, so it checks the player first."""
    w = setup_world(t_wizard)
    denied(w["player"], template.format(pk=w["statue"].pk))
    statue = Object.global_objects.get(pk=w["statue"].pk)
    assert not statue.recycled
    assert not statue.aliases.filter(alias="rock").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eject_needs_write_on_the_container(t_init: Object, t_wizard: Object):
    """``eject`` moves the victim as the Wizard, so ``@eject`` checks the container."""
    w = setup_world(t_wizard)
    denied(w["player"], f"@eject Wizard Statue from #{w['hall'].pk}")
    w["statue"].refresh_from_db()
    assert w["statue"].location == w["hall"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_plain_player_cannot_lock_a_foreign_exit(t_init: Object, t_wizard: Object):
    """``lock`` lives on ``$room``, so any player in a room could lock its exits."""
    w = setup_world(t_wizard)
    denied(w["player"], "lock east")
    with code.ContextManager(t_wizard, lambda _: None):
        assert not w["door"].is_locked()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_for_verbs_need_write(t_init: Object, t_wizard: Object):
    """The note and container lock verbs said "owner only" but did not check."""
    w = setup_world(t_wizard)
    denied(w["player"], f"@lock_for_read #{w['memo'].pk} with me")
    denied(w["player"], f"@unlock_for_read #{w['memo'].pk}")
    denied(w["player"], f"@lock_for_open #{w['chest'].pk} with me")
    denied(w["player"], f"@unlock_for_open #{w['chest'].pk}")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
@pytest.mark.parametrize(
    "expr",
    [
        "lookup({hall}).describe('hacked')",
        "lookup({hall}).set_name('Pwned')",
        "lookup({hall}).add_exit(lookup({door}))",
        "lookup({hall}).remove_exit(lookup({door}))",
        "lookup({vault}).add_entrance(lookup({door}))",
        "lookup({vault}).remove_entrance(lookup({door}))",
        "lookup({vault}).bless_for_entry(context.player)",
        "lookup({hall}).eject(lookup({statue}))",
        "lookup({chest}).set_opened(True)",
        "lookup({chest}).set_opaque(2)",
        "lookup({statue}).moveto(context.player)",
        "lookup({hall}).moveto(context.player)",
    ],
)
def test_helper_verbs_check_caller_perms(t_init: Object, t_wizard: Object, expr):
    """
    A helper verb is Wizard-owned and executable by everyone. Called from a
    programmer's ``@eval``, it changed any object as the Wizard. Each helper now
    checks ``caller_perms()``, which is the programmer here.
    """
    w = setup_world(t_wizard, programmer=True)
    ids = {k: v.pk for k, v in w.items()}
    out = run(w["player"], f'@eval "{expr.format(**ids)}"')
    assert any("not allowed" in line for line in out), out
    hall = Object.global_objects.get(pk=w["hall"].pk)
    assert hall.name == "Wizard Hall"
    w["statue"].refresh_from_db()
    assert w["statue"].location == w["hall"]
    with code.ContextManager(t_wizard, lambda _: None):
        assert hall.get_property("exits") == [w["door"]]
        assert w["vault"].get_property("entrances") == [w["door"]]
        assert hall.get_property("description") != "hacked"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_player_may_move_themselves_through_any_code(t_init: Object, t_wizard: Object):
    """``moveto`` exempts the player who started the task, so a builder's slide or teleporter still works."""
    w = setup_world(t_wizard, programmer=True)
    run(w["player"], f'@eval "context.player.moveto(lookup({w["den"].pk}))"')
    w["player"].refresh_from_db()
    assert w["player"].location == w["den"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_still_moves_wizard_owned_things(t_init: Object, t_wizard: Object):
    """``take`` is Wizard-owned, so its ``moveto`` call passes the caller check."""
    w = setup_world(t_wizard)
    run(w["player"], "take Wizard Statue")
    w["statue"].refresh_from_db()
    assert w["statue"].location == w["player"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_caller_perms_is_the_calling_owner(t_init: Object, t_wizard: Object):
    """``caller_perms()`` returns the owner of the code one frame out, not the verb's own owner."""
    w = setup_world(t_wizard, programmer=True)
    with code.ContextManager(t_wizard, lambda _: None):
        w["statue"].add_verb("who", code="from moo.sdk import caller_perms\nreturn caller_perms()")
    out = run(w["player"], f'@eval "lookup({w["statue"].pk}).who()"')
    assert out == [repr(w["player"])]
