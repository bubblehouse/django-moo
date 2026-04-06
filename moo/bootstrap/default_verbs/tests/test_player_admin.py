import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object
from moo.core.models.verb import Verb, VerbName
from moo.core.exceptions import UsageError
from .utils import save_quietly

# --- @create ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_create_basic_lands_in_inventory(t_init: Object, t_wizard: Object):
    """@create <name> creates an object and places it in the player's inventory."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@create "red ball"')
    assert any("Created" in line for line in printed)
    assert t_wizard.contents.filter(name="red ball").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_create_from_parent(t_init: Object, t_wizard: Object):
    """@create <name> from <parent> creates an object with the specified parent."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@create "widget" from $thing')
    assert any("Created" in line for line in printed)
    assert any("Transmuted" in line for line in printed)
    obj = t_wizard.contents.filter(name="widget").first()
    assert obj is not None
    assert obj.parents.filter(pk=system.thing.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_create_in_void(t_init: Object, t_wizard: Object):
    """@create <name> in void creates an object with no location."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@create "ghost" in void')
    assert any("Created" in line for line in printed)
    assert any("void" in line for line in printed)
    obj = Object.objects.filter(name="ghost").first()
    assert obj is not None
    assert obj.location is None
    assert not t_wizard.contents.filter(name="ghost").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_create_in_location(t_init: Object, t_wizard: Object):
    """@create <name> in <room> creates an object placed in the given room."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = create("Test Room", parents=[system.room])
        parse.interpret(ctx, '@create "token" in "Test Room"')
    assert any("Created" in line for line in printed)
    obj = Object.objects.filter(name="token").first()
    assert obj is not None
    room.refresh_from_db()
    assert obj.location == room


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_create_from_parent_in_void(t_init: Object, t_wizard: Object):
    """@create <name> from <parent> in void combines both prepositions."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@create "phantom" from $thing in void')
    assert any("Created" in line for line in printed)
    assert any("Transmuted" in line for line in printed)
    assert any("void" in line for m in printed for line in [str(m)])
    obj = Object.objects.filter(name="phantom").first()
    assert obj is not None
    assert obj.location is None
    assert obj.parents.filter(pk=system.thing.pk).exists()


# --- whodunnit ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_whodunnit_all_wizards(t_init: Object, t_wizard: Object):
    """whodunnit() returns None when all callers are wizards."""
    with code.ContextManager(t_wizard, lambda _: None):
        callers = [{"caller": t_wizard, "verb_name": "tell", "this": t_wizard}]
        result = t_wizard.whodunnit(callers, [], [])
    assert result is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_whodunnit_finds_non_wizard(t_init: Object, t_wizard: Object):
    """whodunnit() returns the frame dict for a non-wizard in the mistrust list."""
    with code.ContextManager(t_wizard, lambda _: None):
        player_obj = lookup("Player")
        callers = [{"caller": player_obj, "verb_name": "some_verb", "this": player_obj}]
        result = t_wizard.whodunnit(callers, [], [player_obj])
    assert result is not None
    assert result["caller"] == player_obj
    assert result["verb_name"] == "some_verb"


# --- @lock ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_object_with_key(t_init: Object, t_wizard: Object, setup_item):
    """@lock <obj> with <key> sets the key property on the object."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, f"@lock widget with #{widget.id}")
        widget.refresh_from_db()
    assert widget.get_property("key") is not None


# --- @unlock ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_unlock_clears_key(t_init: Object, t_wizard: Object, setup_item):
    """@unlock <obj> clears the key property on the object."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        widget.set_property("key", "somekey")
        parse.interpret(ctx, "@unlock widget")
        widget.refresh_from_db()
    assert widget.get_property("key") is None


# --- @eject ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eject_victim_from_container(t_init: Object, t_wizard: Object):
    """@eject <victim> from <container> removes the victim and sends ejection messages."""
    system = lookup(1)
    player_npc = lookup("Player")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        container = create("Vault", parents=[system.room], location=t_wizard.location)
        player_npc.location = container
        save_quietly(player_npc)
        for name, code_str in [
            ("victim_ejection_msg", 'return "You have been ejected!"'),
            ("ejection_msg", 'return "You ejected them."'),
            ("oejection_msg", 'return "They were ejected."'),
            ("eject", "victim = args[0]; victim.location = this.location; victim.save()"),
        ]:
            v = Verb.objects.create(origin=container, owner=t_wizard, code=code_str)
            VerbName.objects.create(verb=v, name=name)
        with pytest.warns(RuntimeWarning) as w:
            parse.interpret(ctx, "@eject Player from Vault")
        player_npc.refresh_from_db()
    messages = [str(x.message) for x in w.list]
    assert any("You have been ejected!" in m for m in messages)
    assert any("They were ejected." in m for m in messages)
    assert "You ejected them." in printed
    assert player_npc.location != container


# --- @quota ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_quota_own(t_init: Object, t_wizard: Object):
    """@quota without an argument shows the player's own quota."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@quota")
    assert any("Your quota is" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_quota_other_wizard(t_init: Object, t_wizard: Object):
    """@quota <player> shows another player's quota when the caller is a wizard."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@quota Player")
    assert any("Player's quota is" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_quota_other_non_wizard_denied(t_init: Object, t_wizard: Object):
    """@quota <player> produces no output for a non-wizard querying another player's quota."""
    printed = []
    player_npc = lookup("Player")
    with code.ContextManager(player_npc, printed.append) as ctx:
        parse.interpret(ctx, "@quota Wizard")
    assert not any("Wizard's quota is" in line for line in printed)


# --- @whereis ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_whereis_finds_player(t_init: Object, t_wizard: Object):
    """@whereis <player> prints the player's current location."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@whereis Player")
    assert any("Player" in line for line in printed)
    assert any("in" in line for line in printed)


# --- @sweep ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sweep_finds_listener(t_init: Object, t_wizard: Object):
    """@sweep reports connected players in the room as listeners."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@sweep")
    assert any("is listening" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sweep_secure_room(t_init: Object, t_wizard: Object):
    """@sweep reports 'Communications are secure.' when no suspicious verbs are found."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@sweep")
    assert any("Communications are secure." in line for line in printed)


# --- @check ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_check_scans_responsible(t_init: Object, t_wizard: Object):
    """@check scans the responsible log and reports non-wizard message sources."""
    printed = []
    player_npc = lookup("Player")
    callers_frame = [{"caller": player_npc, "verb_name": "tell", "this": player_npc}]
    with code.ContextManager(t_wizard, printed.append) as ctx:
        t_wizard.set_property("responsible", [[callers_frame, ("suspicious message",)]])
        parse.interpret(ctx, "@check 5 !Player")
    assert any("sent message" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_check_tracks_multiple_senders(t_init: Object, t_wizard: Object):
    """@check identifies all 3 non-wizard senders tracked via tell() with paranoid=1."""
    system = lookup(1)
    player_npc = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None):
        alice = create("Alice", parents=[system.player], location=t_wizard.location)
        bob = create("Bob", parents=[system.player], location=t_wizard.location)

    t_wizard.set_property("paranoid", 1)

    for sender, msg in [
        (player_npc, "msg from player"),
        (alice, "msg from alice"),
        (bob, "msg from bob"),
    ]:
        with code.ContextManager(sender, lambda _: None):
            with pytest.warns(RuntimeWarning):
                t_wizard.tell(msg)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        t_wizard.refresh_from_db()
        parse.interpret(ctx, "@check 10 !Player !Alice !Bob")
    assert sum(1 for line in printed if "sent message" in line) == 3


# --- @show ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_show_object_details(t_init: Object, t_wizard: Object, setup_item):
    """@show <obj> prints the object's owner, location, parents, verbs, and properties."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, "@show widget")
    assert any("Owner:" in line for line in printed)
    assert any("Location:" in line for line in printed)
    assert any("Verbs:" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_show_global_lookup(t_init: Object, t_wizard: Object, setup_item):
    """@show resolves objects globally, not just in the current room."""
    other_room = create("Other Room", parents=[lookup("$room")])
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        # Place the widget in a different room from the wizard
        setup_item(other_room, "remote_widget")
        parse.interpret(ctx, "@show remote_widget")
    assert any("Owner:" in line for line in printed)
    assert any("Location:" in line for line in printed)


# --- @alias ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_alias_by_name(t_init: Object, t_wizard: Object, setup_item):
    """@alias <object> as <alias> adds an alias to an object by name."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, '@alias widget as "gadget"')
        widget.refresh_from_db()

    # Verify alias was added
    assert widget.aliases.filter(alias="gadget").exists()
    assert any("Added alias" in line for line in printed)
    assert any("gadget" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_alias_by_object_id(t_init: Object, t_wizard: Object, setup_item):
    """@alias #N as <alias> adds an alias to an object by ID."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, f'@alias #{widget.id} as "thing"')
        widget.refresh_from_db()

    # Verify alias was added
    assert widget.aliases.filter(alias="thing").exists()
    assert any("Added alias" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_alias_multiple_aliases(t_init: Object, t_wizard: Object, setup_item):
    """Multiple @alias commands add multiple aliases to the same object."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "pool table")
        parse.interpret(ctx, '@alias "pool table" as "table"')
        parse.interpret(ctx, '@alias "pool table" as "pool"')
        widget.refresh_from_db()

    # Verify both aliases were added
    assert widget.aliases.filter(alias="table").exists()
    assert widget.aliases.filter(alias="pool").exists()


# --- @rename ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rename_own_object(t_init: Object, t_wizard: Object, setup_item):
    """@rename <obj> to <name> changes the object's name."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, "@rename widget to gadget")
        widget.refresh_from_db()
    assert widget.name == "gadget"
    assert any("gadget" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rename_permission_denied(t_init: Object, t_wizard: Object, setup_item):
    """Non-owner cannot rename an object."""
    player_npc = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None):
        widget = setup_item(t_wizard.location, "widget")
    printed = []
    with code.ContextManager(player_npc, printed.append) as ctx:
        parse.interpret(ctx, "@rename widget to gadget")
        widget.refresh_from_db()
    assert widget.name == "widget"
    assert any("Permission denied" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rename_requires_to_clause(t_init: Object, t_wizard: Object, setup_item):
    """@rename without 'to' raises UsageError."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        setup_item(t_wizard.location, "widget")
        with pytest.raises(UsageError):
            parse.interpret(ctx, "@rename widget")


# --- @version / @memory ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_version_wizard(t_init: Object, t_wizard: Object):
    """@version prints version, python, and PID lines for a wizard."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@version")
    output = "\n".join(printed)
    assert "Version:" in output
    assert "Python:" in output
    assert "PID:" in output


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_version_non_wizard_denied(t_init: Object, t_wizard: Object):
    """@version is denied for non-wizards."""
    player_npc = lookup("Player")
    printed = []
    with code.ContextManager(player_npc, printed.append) as ctx:
        parse.interpret(ctx, "@version")
    assert any("Permission denied" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_memory_wizard(t_init: Object, t_wizard: Object):
    """@memory prints memory info or an unavailable message for a wizard."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@memory")
    output = "\n".join(printed)
    assert "Memory" in output or "unavailable" in output


# --- @add_parent / @remove_parent ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_add_parent_by_id(t_init: Object, t_wizard: Object):
    """@add_parent #N to <parent> adds a parent to the object."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("plain thing", location=t_wizard)
        parse.interpret(ctx, f"@add_parent #{obj.pk} to $thing")
    obj.refresh_from_db()
    assert obj.parents.filter(pk=system.thing.pk).exists()
    assert any("Added" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_remove_parent_by_id(t_init: Object, t_wizard: Object):
    """@remove_parent #N from <parent> removes a parent from the object."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("plain thing", location=t_wizard)
        obj.parents.add(system.thing)
        assert obj.parents.filter(pk=system.thing.pk).exists()
        parse.interpret(ctx, f"@remove_parent #{obj.pk} from $thing")
    obj.refresh_from_db()
    assert not obj.parents.filter(pk=system.thing.pk).exists()
    assert any("Removed" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reparent_move_pattern(t_init: Object, t_wizard: Object):
    """Remove $furniture parent, move object, re-add parent — the reparent-move pattern."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room_a = create("Room A", parents=[system.room], location=t_wizard.location)
        room_b = create("Room B", parents=[system.room], location=t_wizard.location)
        # Create furniture in room_a directly (bypasses moveto)
        obj = create("oak bench", parents=[system.furniture], location=room_a)
        pk = obj.pk
        # Add $thing first so moveto is reachable during the move
        parse.interpret(ctx, f"@add_parent #{pk} to $thing")
        # Strip $furniture (its moveto blocks non-wizard movement)
        parse.interpret(ctx, f"@remove_parent #{pk} from $furniture")
        # Move using $thing.moveto
        parse.interpret(ctx, f"@move #{pk} to #{room_b.pk}")
        # Clean up the temporary $thing parent, restore $furniture
        parse.interpret(ctx, f"@remove_parent #{pk} from $thing")
        parse.interpret(ctx, f"@add_parent #{pk} to $furniture")
    obj.refresh_from_db()
    assert obj.location == room_b
    assert obj.parents.filter(pk=system.furniture.pk).exists()
