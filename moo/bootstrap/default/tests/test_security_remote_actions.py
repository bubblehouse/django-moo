"""
Wizard-owned verbs called as methods, from anywhere.

The command parser only matches objects near the player, so a verb such as
``take`` never had to ask where its object was. Called as a method from
``@eval``, or from a ``@set ... to <expression>`` that any ``$builder`` can type,
it takes any object, and its Wizard owner passes every ``moveto`` check. These
tests cover the movement verbs, ``@show``, object names, ``report``, and the
property rows that adding a parent copies onto an object.
"""

import pytest

from moo.core import code, parse
from moo.core.exceptions import QuotaError, UserError
from moo.core.models import AuditLog, Object
from moo.core.models.acl import Access
from moo.sdk import create, lookup, within_reach


def setup_world(t_wizard):
    """
    Return a ``$builder`` standing in a Wizard-owned hall, and the things around it.

    The Wizard stands in a second room, the vault, holding a wallet. An open chest
    in the vault holds a coin. An exit leads from the hall to the vault.
    """
    sys = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None):
        hall = create("Wizard Hall", parents=[sys.room], location=None)
        vault = create("Wizard Vault", parents=[sys.room], location=None)
        door = create("vault door", parents=[sys.exit], location=None)
        door.add_alias("east")
        door.set_property("source", hall)
        door.set_property("dest", vault)
        hall.add_exit(door)
        vault.add_entrance(door)
        wallet = create("Wizard Wallet", parents=[sys.thing], location=t_wizard)
        chest = create("Vault Chest", parents=[sys.container], location=vault)
        chest.set_opened(True)
        coin = create("Gold Coin", parents=[sys.thing], location=chest)
        statue = create("Hall Statue", parents=[sys.thing], location=hall)
        t_wizard.location = vault
        t_wizard.save()
        p = lookup("Player")
        p.parents.add(sys.builder)
        p.location = hall
        p.save()
    return {
        "player": p,
        "hall": hall,
        "vault": vault,
        "door": door,
        "wallet": wallet,
        "chest": chest,
        "coin": coin,
        "statue": statue,
    }


def run(avatar, line):
    """Run one command as `avatar` and return its printed output."""
    out = []
    with code.ContextManager(avatar, out.append) as ctx:
        parse.interpret(ctx, line)
    return out


def location_of(obj):
    """Return `obj`'s location as stored in the database."""
    return Object.global_objects.get(pk=obj.pk).location


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_refuses_a_thing_in_another_players_inventory(t_init: Object, t_wizard: Object):
    """
    ``lookup(wallet).take()`` used to pull the Wizard's wallet out of their inventory
    from another room: ``moveto`` saw ``take``'s Wizard owner as its caller. ``take``
    now refuses a thing that is not within the player's reach.
    """
    w = setup_world(t_wizard)
    out = run(w["player"], f"@set loot on me to lookup({w['wallet'].pk}).take()")
    assert any("can't reach" in line for line in out), out
    assert location_of(w["wallet"]) == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_still_works_in_the_same_room(t_init: Object, t_wizard: Object):
    """A thing in the player's room is within reach, typed or called as a method."""
    w = setup_world(t_wizard)
    run(w["player"], "take Hall Statue")
    assert location_of(w["statue"]) == w["player"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_container_take_refuses_a_container_in_another_room(t_init: Object, t_wizard: Object):
    """``lookup(chest).take(lookup(coin))`` emptied an open container anywhere in the world."""
    w = setup_world(t_wizard)
    out = run(w["player"], f"@set loot on me to lookup({w['chest'].pk}).take(lookup({w['coin'].pk}))")
    assert any("can't reach" in line for line in out), out
    assert location_of(w["coin"]) == w["chest"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_container_put_refuses_someone_elses_thing(t_init: Object, t_wizard: Object):
    """
    ``lookup(my_box).put(lookup(wallet))`` moved any object into the player's own
    container. ``put`` now needs both the thing and the container within reach.
    """
    w = setup_world(t_wizard)
    sys = lookup(1)
    with code.ContextManager(w["player"], lambda _: None):
        box = create("Player Box", parents=[sys.container], location=w["player"])
    with code.ContextManager(t_wizard, lambda _: None):
        box.set_opened(True)
    out = run(w["player"], f"@set loot on me to lookup({box.pk}).put(lookup({w['wallet'].pk}))")
    assert any("can't reach" in line for line in out), out
    assert location_of(w["wallet"]) == t_wizard
    run(w["player"], f"@set loot on me to lookup({box.pk}).put(lookup({w['statue'].pk}))")
    assert location_of(w["statue"]) == box


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_exit_invoke_refuses_another_player(t_init: Object, t_wizard: Object):
    """``lookup(door).invoke(lookup(victim))`` marched another player through any exit."""
    w = setup_world(t_wizard)
    with code.ContextManager(t_wizard, lambda _: None):
        t_wizard.location = w["hall"]
        t_wizard.save()
    with pytest.raises(PermissionError):
        run(w["player"], f"@set x on me to lookup({w['door'].pk}).invoke(lookup({t_wizard.pk}))")
    assert location_of(t_wizard) == w["hall"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_exit_move_needs_the_thing_at_the_exit(t_init: Object, t_wizard: Object):
    """
    ``exit.move(thing)`` never checked where `thing` was, so a player could call
    any exit's ``move`` with an object from anywhere, or with themselves to
    teleport. Only something standing at the exit's source goes through it.
    """
    w = setup_world(t_wizard)
    with code.ContextManager(w["player"], lambda _: None):
        den = create("Player Den", parents=[lookup(1).room], location=None)
    with code.ContextManager(t_wizard, lambda _: None):
        w["player"].location = den
        w["player"].save()
    run(w["player"], f"@set x on me to lookup({w['door'].pk}).invoke(context.player)")
    assert location_of(w["player"]) == den
    with pytest.raises(PermissionError):
        run(w["player"], f"@set x on me to lookup({w['door'].pk}).move(lookup({w['statue'].pk}))")
    assert location_of(w["statue"]) == w["hall"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_walking_through_an_exit_still_works(t_init: Object, t_wizard: Object):
    """A player standing at the exit's source still goes through it."""
    w = setup_world(t_wizard)
    with pytest.warns(RuntimeWarning):
        run(w["player"], "go east")
    assert location_of(w["player"]) == w["vault"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_within_reach(t_init: Object, t_wizard: Object):
    """Inventory, the room and open containers there are within reach; other rooms and players are not."""
    w = setup_world(t_wizard)
    with code.ContextManager(w["player"], lambda _: None):
        assert within_reach(w["statue"])
        assert not within_reach(w["wallet"])
        assert not within_reach(w["coin"])
        assert not within_reach(w["chest"])
    with code.ContextManager(t_wizard, lambda _: None):
        assert within_reach(w["wallet"])
        assert within_reach(w["coin"])


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_give_refuses_a_thing_out_of_reach(t_init: Object, t_wizard: Object):
    """``give`` moves its gift with the Wizard's permissions, so it checks that the gift is within reach."""
    w = setup_world(t_wizard)
    with code.ContextManager(t_wizard, lambda _: None):
        t_wizard.location = w["hall"]
        t_wizard.save()
    out = run(w["player"], f"give #{w['coin'].pk} to Wizard")
    assert any("can't reach" in line for line in out), out
    assert location_of(w["coin"]) == w["chest"]
    run(w["player"], "give Hall Statue to Wizard")
    assert location_of(w["statue"]) == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_show_needs_read_on_the_object(t_init: Object, t_wizard: Object):
    """
    ``@show`` checked ``read`` on each property row and never on the object. A
    private object whose rows kept the default everyone-read rule, such as a game's
    ledger of player records, printed every row to any player.
    """
    w = setup_world(t_wizard)
    with code.ContextManager(t_wizard, lambda _: None):
        ledger = create("Private Ledger", location=None)
        ledger.set_property("p2", {"secret": "the player behind the mask"})
    Access.objects.filter(object=ledger, group="everyone", permission__name="read").delete()
    for line in (f"@show #{ledger.pk}", f"@show p2 on #{ledger.pk}"):
        with pytest.raises(PermissionError):
            run(w["player"], line)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_show_still_shows_readable_things(t_init: Object, t_wizard: Object):
    """``@show`` on a readable object, and ``@show <prop> on <object>``, still print, without the old crash."""
    w = setup_world(t_wizard)
    with code.ContextManager(t_wizard, lambda _: None):
        w["statue"].set_property("motto", "hello")
    out = run(w["player"], f"@show #{w['statue'].pk}")
    assert any("motto:" in str(line) and "hello" in str(line) for line in out), out
    run(w["player"], f"@show motto on #{w['statue'].pk}")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
@pytest.mark.parametrize("name", ["[bold red]SYSTEM[/bold red] Wizard", "Bell\x07", "Esc\x1b[2J", "Two\nLines"])
def test_names_refuse_markup_and_control_characters(t_init: Object, t_wizard: Object, name):
    """A name is printed unescaped to other players, so it can't hold markup or terminal escapes."""
    w = setup_world(t_wizard)
    with pytest.raises(UserError):
        with code.ContextManager(w["player"], lambda _: None):
            create(name, location=None)
    with pytest.raises(UserError):
        with code.ContextManager(w["player"], lambda _: None):
            w["player"].name = name
            w["player"].save()
    assert Object.global_objects.get(pk=w["player"].pk).name == "Player"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_report_has_a_cooldown(t_init: Object, t_wizard: Object):
    """Every report writes an audit row and mails the staff, so one account files one report per cooldown."""
    player = lookup("Player")
    out = run(player, "report Wizard for one")
    out += run(player, "report Wizard for two")
    assert any("Wait a moment" in line for line in out), out
    assert AuditLog.objects.filter(action="report").count() == 1
    with code.ContextManager(t_wizard, lambda _: None):
        lookup(1).set_property("report_cooldown", 0)
    run(player, "report Wizard for three")
    assert AuditLog.objects.filter(action="report").count() == 2


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
@pytest.mark.parametrize("inherit_owner", [False, True])
def test_add_parent_does_not_take_over_existing_rows(t_init: Object, t_wizard: Object, inherit_owner):
    """
    Adding a parent re-owned every existing row that matched one of the parent's
    rows. A ``$builder`` made a throwaway parent with an ``ownership_quota`` row,
    added it to their own avatar, and then owned their Wizard-owned quota row, so
    ``@set ownership_quota on me to 99999`` worked. Existing rows now keep their owner.
    """
    w = setup_world(t_wizard)
    p = w["player"]
    with code.ContextManager(p, lambda _: None):
        shim = create("Shim", location=None)
        shim.set_property("ownership_quota", 0, inherit_owner=inherit_owner)
    run(p, "@add_parent Shim to me")
    with code.ContextManager(t_wizard, lambda _: None):
        row = p.get_property("ownership_quota", recurse=False, original=True)
    assert row.owner == t_wizard
    assert row.inherit_owner
    with pytest.raises(PermissionError):
        run(p, "@set ownership_quota on me to 99999")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_a_quota_that_is_not_a_number_is_used_up(t_init: Object, t_wizard: Object):
    """A quota row holding anything but an int used to mean "no quota"; it now means none left."""
    w = setup_world(t_wizard)
    p = w["player"]
    with code.ContextManager(t_wizard, lambda _: None):
        p.set_property("ownership_quota", "lots")
    with pytest.raises(QuotaError):
        with code.ContextManager(p, lambda _: None):
            create("Freebie", location=None)
