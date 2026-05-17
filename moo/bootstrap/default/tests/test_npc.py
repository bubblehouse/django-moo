# pylint: disable=no-value-for-parameter,unused-variable
"""
Tests for the $npc class — autonomous actors built on $player + $daemon.

Covers:
  - Generic NPC exists with both $player and $daemon as direct parents
  - $daemon's recycle wins the depth-1 tie (PT cleanup on delete)
  - initialize hook creates an anonymous Player record (is_player() True)
  - tell() is harmless on an unconnected NPC
  - take refuses (inherited from $player.take)
  - on_tick calls act(); subclass act override runs
  - say announces in the NPC's room
  - recycle removes the Player record AND the PeriodicTask
  - Generic Wanderer exists as an $npc descendant
  - $wanderer.act moves between marked rooms; empty destinations is a no-op
  - @npc create makes a wired-up NPC (Object + Player record + location)
  - @npc destinations reads and writes wander_rooms
  - @npc create from $wanderer produces a $wanderer instance
"""

import pytest

from moo.core import code, exceptions, parse
from moo.core.models import Object
from moo.sdk import create, lookup
from .utils import setup_room


def _make_npc(name="alice", parents=None, location=None):
    npc_cls = lookup("Generic NPC")
    return create(name, parents=[parents or npc_cls], location=location)


def _periodic_task_count(pk):
    from django_celery_beat.models import PeriodicTask

    return PeriodicTask.objects.filter(pk=pk).count()


def _player_row_count(obj):
    from moo.core.models.auth import Player

    return Player.objects.filter(avatar=obj).count()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_npc_class_exists(t_init: Object, t_wizard: Object):
    """$npc has both $player and $daemon as direct parents."""
    npc_cls = lookup("Generic NPC")
    player_cls = lookup("Generic Player")
    daemon_cls = lookup("Generic Daemon")
    parent_pks = {p.pk for p in npc_cls.parents.all()}
    assert parent_pks == {player_cls.pk, daemon_cls.pk}


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_npc_default_props(t_init: Object, t_wizard: Object):
    """NPCs inherit daemon scheduling props with $npc's overrides."""
    with code.ContextManager(t_wizard, lambda s: None):
        npc = _make_npc(location=t_wizard)
        assert npc.get_property("interval") == 30
        assert npc.get_property("periodic_task_id") is None
        assert npc.get_property("tick_count") == 0
        assert "nondescript" in npc.get_property("description")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_npc_initialize_creates_player_record(t_init: Object, t_wizard: Object):
    """create() runs initialize via eager Celery — Player row exists on return."""
    with code.ContextManager(t_wizard, lambda s: None):
        npc = _make_npc()
        assert _player_row_count(npc) == 1
        assert npc.is_player()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_npc_tell_does_not_raise(t_init: Object, t_wizard: Object):
    """tell() on an NPC routes through $player.tell -> $root_class.tell and
    completes without raising. The conftest mock forces is_connected=True so
    write() actually fires (and emits a benign RuntimeWarning); that's an
    artifact of the test harness, not of $npc."""
    with code.ContextManager(t_wizard, lambda s: None):
        npc = _make_npc()
        with pytest.warns(RuntimeWarning):
            npc.tell("hello")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_npc_take_refused(t_init: Object, t_wizard: Object):
    """`take <npc>` dispatches $player.take and prints the refusal."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        npc = _make_npc(location=room)
        printed.clear()
        parse.interpret(ctx, f"take {npc.name}")
    assert any("can't take a player" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_npc_tick_calls_act(t_init: Object, t_wizard: Object):
    """A subclass act override runs through tick -> on_tick -> act."""
    npc_cls = lookup("Generic NPC")
    with code.ContextManager(t_wizard, lambda s: None):
        sub = create("Counting NPC", parents=[npc_cls], owner=t_wizard)
        sub.set_property("count", 0, inherit_owner=True)
        sub.add_verb(
            "act",
            code="this.set_property('count', this.get_property('count') + 1)",
        )
        instance = create("counter_npc", parents=[sub], location=t_wizard, owner=t_wizard)
        instance.trigger()
        instance.trigger()
        assert instance.get_property("count") == 2
        assert instance.get_property("tick_count") == 2


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_npc_say_announces_to_room(t_init: Object, t_wizard: Object):
    """npc.say('hi') broadcasts '<name>: hi' to the room minus the NPC.

    Tests run with the memory:// Celery broker, so ``write()`` (the leaf of
    the ``tell`` chain) emits the message as a ``RuntimeWarning`` rather
    than going out to a real queue. Inspect the warning text to verify the
    announce reached the wizard.
    """
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        npc = _make_npc(location=room)
        npc_name = npc.name
        with pytest.warns(RuntimeWarning) as warns:
            npc.say("hi")
    messages = [str(w.message) for w in warns]
    assert any(f"{npc_name}: hi" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_npc_recycle_cleans_pt_and_player(t_init: Object, t_wizard: Object):
    """Deleting an enabled NPC removes both its PeriodicTask and Player row."""
    with code.ContextManager(t_wizard, lambda s: None):
        npc = _make_npc()
        npc.enable()
        pt_id = npc.get_property("periodic_task_id")
        assert pt_id is not None
        assert _periodic_task_count(pt_id) == 1
        npc_pk = npc.pk
        npc.delete()
        assert _periodic_task_count(pt_id) == 0
        from moo.core.models.auth import Player

        assert Player.objects.filter(avatar_id=npc_pk).count() == 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_wanderer_class_exists(t_init: Object, t_wizard: Object):
    """$wanderer is a direct child of $npc."""
    wanderer_cls = lookup("Generic Wanderer")
    npc_cls = lookup("Generic NPC")
    assert npc_cls in wanderer_cls.parents.all()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_wanderer_moves_between_rooms(t_init: Object, t_wizard: Object):
    """With two candidate rooms, the wanderer alternates between them on each tick."""
    wanderer_cls = lookup("Generic Wanderer")
    rooms_cls = lookup("Generic Room")
    with code.ContextManager(t_wizard, lambda s: None):
        room_a = create("Room A", parents=[rooms_cls])
        room_b = create("Room B", parents=[rooms_cls])
        npc = create("Walker", parents=[wanderer_cls], location=room_a)
        npc.set_property("wander_rooms", [room_a.pk, room_b.pk])

        npc.trigger()
        npc.refresh_from_db()
        assert npc.location == room_b

        npc.trigger()
        npc.refresh_from_db()
        assert npc.location == room_a


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_wanderer_empty_destinations_noop(t_init: Object, t_wizard: Object):
    """No wander_rooms -> the wanderer stays put."""
    wanderer_cls = lookup("Generic Wanderer")
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        npc = create("Idle Walker", parents=[wanderer_cls], location=room)
        npc.trigger()
        npc.refresh_from_db()
        assert npc.location == room


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_npc_create_default_parent(t_init: Object, t_wizard: Object):
    """@npc create <name> makes a $npc child in the wizard's current room."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        printed.clear()
        parse.interpret(ctx, "@npc create alice")
        npc = lookup("alice")
        assert npc.location == room
        npc_cls = lookup("Generic NPC")
        assert npc.is_a(npc_cls)
        assert _player_row_count(npc) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_npc_create_from_wanderer(t_init: Object, t_wizard: Object):
    """@npc create alice from "Generic Wanderer" produces a wanderer instance."""
    with code.ContextManager(t_wizard, lambda s: None) as ctx:
        room = setup_room(t_wizard)
        parse.interpret(ctx, '@npc create alice from "Generic Wanderer"')
        npc = lookup("alice")
        wanderer_cls = lookup("Generic Wanderer")
        assert npc.is_a(wanderer_cls)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_npc_destinations_set_and_read(t_init: Object, t_wizard: Object):
    """@npc destinations writes, then reads back, the wander_rooms list."""
    rooms_cls = lookup("Generic Room")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        room_a = create("Plaza", parents=[rooms_cls])
        room_b = create("Atrium", parents=[rooms_cls])
        parse.interpret(ctx, "@npc create alice")
        printed.clear()
        parse.interpret(ctx, f"@npc destinations alice {room_a.pk} {room_b.pk}")
        npc = lookup("alice")
        assert npc.get_property("wander_rooms") == [room_a.pk, room_b.pk]
        printed.clear()
        parse.interpret(ctx, "@npc destinations alice")
    output = "\n".join(printed)
    assert "Plaza" in output and "Atrium" in output


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_npc_nonwizard_denied(t_init: Object, t_wizard: Object):
    """@npc is on $wizard — non-wizards can't even resolve the verb."""
    with code.ContextManager(t_wizard, lambda s: None):
        player_cls = lookup("Generic Player")
        peon = create("peon_npc", parents=[player_cls], owner=t_wizard)
    printed = []
    with code.ContextManager(peon, printed.append) as ctx:
        try:
            parse.interpret(ctx, "@npc create alice")
        except (exceptions.NoSuchVerbError, exceptions.UserError, PermissionError):
            return
    assert not any("Created" in line for line in printed)
