import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object
from moo.core.models.verb import Verb, VerbName
from .utils import save_quietly


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
            ("ejection_msg",        'return "You ejected them."'),
            ("oejection_msg",       'return "They were ejected."'),
            ("eject",               'victim = args[0]; victim.location = this.location; victim.save()'),
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
        (alice,      "msg from alice"),
        (bob,        "msg from bob"),
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
