import pytest

from moo.core import code, lookup, parse
from moo.core.models import Object


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


@pytest.mark.skip(reason="depends on _.lock_utils.parse_keyexp() being implemented")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_object_with_key(t_init: Object, t_wizard: Object):
    """@lock <obj> with <key> sets the key property on the object."""
    pass


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


@pytest.mark.skip(reason="requires container with victim_ejection_msg / ejection_msg / eject verbs")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eject_victim_from_container(t_init: Object, t_wizard: Object):
    """@eject <victim> from <container> removes the victim and sends ejection messages."""
    pass


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


# --- @whereis ---


@pytest.mark.skip(reason="requires player.whereis_location_msg() verb to be defined on $player")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_whereis_finds_player(t_init: Object, t_wizard: Object):
    """@whereis <player> prints the player's current location."""
    pass


# --- @sweep ---


@pytest.mark.skip(reason="verb has a bug: `room = player` should be `room = player.location`")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sweep_finds_listener(t_init: Object, t_wizard: Object):
    """@sweep reports connected players in the room as listeners."""
    pass


@pytest.mark.skip(reason="verb has a bug: `room = player` should be `room = player.location`")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sweep_secure_room(t_init: Object, t_wizard: Object):
    """@sweep reports 'Communications are secure.' when no listeners are found."""
    pass


# --- @check ---


@pytest.mark.skip(reason="complex args parsing from parser.words; whodunnit() is tested separately")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_check_scans_responsible(t_init: Object, t_wizard: Object):
    """@check scans the responsible log and reports non-wizard message sources."""
    pass


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
