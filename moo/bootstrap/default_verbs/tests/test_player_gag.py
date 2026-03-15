import pytest

from moo.core import code, parse
from moo.sdk import lookup
from moo.core.models import Object


# --- gag_p ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gag_p_empty(t_init: Object, t_wizard: Object):
    """gag_p() returns False when the gag list is empty."""
    with code.ContextManager(t_wizard, lambda _: None):
        player_obj = lookup("Player")
        assert player_obj.gag_p() is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gag_p_player_gagged(t_init: Object, t_wizard: Object):
    """gag_p() returns True when context.player is in this.gaglist."""
    with code.ContextManager(t_wizard, lambda _: None):
        player_obj = lookup("Player")
        player_obj.gaglist = [t_wizard]
        assert player_obj.gag_p() is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gag_p_player_not_gagged(t_init: Object, t_wizard: Object):
    """gag_p() returns False when context.player is not in this.gaglist."""
    with code.ContextManager(t_wizard, lambda _: None):
        player_obj = lookup("Player")
        t_wizard.gaglist = [t_wizard]
        assert player_obj.gag_p() is False


# --- @gag ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gag_player(t_init: Object, t_wizard: Object):
    """@gag <player> adds the player to the caller's gaglist."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player_obj = lookup("Player")
        parse.interpret(ctx, "@gag Player")
        t_wizard.refresh_from_db()
    assert player_obj in t_wizard.gaglist
    assert "Gag list updated." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gag_object(t_init: Object, t_wizard: Object, setup_item):
    """@gag <object> adds a non-player object to the caller's object_gaglist."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, "@gag widget")
        t_wizard.refresh_from_db()
    assert widget in t_wizard.object_gaglist
    assert "Gag list updated." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gag_already_gagged_player(t_init: Object, t_wizard: Object):
    """@gag on an already-gagged player prints a duplicate message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player_obj = lookup("Player")
        t_wizard.gaglist = [player_obj]
        parse.interpret(ctx, "@gag Player")
    assert "You are already gagging Player." in printed
    assert "No changes made to gag list." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gag_already_gagged_object(t_init: Object, t_wizard: Object, setup_item):
    """@gag on an already-gagged object prints a duplicate message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        t_wizard.object_gaglist = [widget]
        parse.interpret(ctx, "@gag widget")
    assert "You are already gagging widget." in printed
    assert "No changes made to gag list." in printed


# --- @ungag ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_ungag_player(t_init: Object, t_wizard: Object):
    """@ungag removes a player from the gag list."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player_obj = lookup("Player")
        t_wizard.gaglist = [player_obj]
        parse.interpret(ctx, "@ungag Player")
        t_wizard.refresh_from_db()
    assert player_obj not in t_wizard.gaglist
    assert any("no longer gagging" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_ungag_everyone(t_init: Object, t_wizard: Object, setup_item):
    """@ungag everyone clears both gag lists."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player_obj = lookup("Player")
        widget = setup_item(t_wizard.location, "widget")
        t_wizard.gaglist = [player_obj]
        t_wizard.object_gaglist = [widget]
        parse.interpret(ctx, "@ungag everyone")
        t_wizard.refresh_from_db()
    assert t_wizard.gaglist == []
    assert t_wizard.object_gaglist == []
    assert "Gag lists cleared." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_ungag_not_gagged(t_init: Object, t_wizard: Object):
    """@ungag on a player not in any list prints 'You are not gagging'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@ungag Player")
    assert any("not gagging" in line for line in printed)


# --- @listgag ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_listgag_empty(t_init: Object, t_wizard: Object):
    """listgag with empty lists prints 'None' for each section."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        t_wizard.listgag()
    assert "Gagged players:" in printed
    assert "Gagged objects:" in printed
    assert printed.count("  None") == 2


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_listgag_with_player(t_init: Object, t_wizard: Object):
    """listgag shows a gagged player's name when the list is non-empty."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        player_obj = lookup("Player")
        t_wizard.gaglist = [player_obj]
        t_wizard.listgag()
    assert any("Player" in line for line in printed)


# --- tell ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_normal(t_init: Object, t_wizard: Object):
    """tell() routes the message to the player via write(), emitting a ConnectionError warning."""
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.warns(RuntimeWarning, match="Hello, world!"):
            t_wizard.tell("Hello, world!")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_gagged_suppressed(t_init: Object, t_wizard: Object):
    """tell() suppresses the message when context.player is in this.gaglist."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        player_obj = lookup("Player")
        player_obj.gaglist = [t_wizard]
        player_obj.tell("You should not see this")
    assert not printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_paranoid_1_stores_responsible(t_init: Object, t_wizard: Object):
    """tell() with paranoid=1 appends callers and message to responsible."""
    with code.ContextManager(t_wizard, lambda _: None):
        player_obj = lookup("Player")
        player_obj.paranoid = 1
        with pytest.warns(RuntimeWarning, match="track me"):
            player_obj.tell("track me")
        player_obj.refresh_from_db()
    assert len(player_obj.responsible) > 0


# --- @paranoid ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_paranoid_sets_level(t_init: Object, t_wizard: Object):
    """@paranoid <level> sets player.paranoid to the given integer level."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        parse.interpret(ctx, "@paranoid 1")
        t_wizard.refresh_from_db()
    assert t_wizard.paranoid == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_paranoid_invalid_level(t_init: Object, t_wizard: Object):
    """@paranoid with an out-of-range level prints an error message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@paranoid 5")
    assert "Paranoid level must be 0, 1, or 2." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_paranoid_level_2(t_init: Object, t_wizard: Object):
    """@paranoid 2 sets the paranoid property to 2."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        parse.interpret(ctx, "@paranoid 2")
        t_wizard.refresh_from_db()
    assert t_wizard.paranoid == 2


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_paranoid_reset_to_0(t_init: Object, t_wizard: Object):
    """@paranoid 0 resets the paranoid property to 0 (disabling tracking)."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        parse.interpret(ctx, "@paranoid 1")
        parse.interpret(ctx, "@paranoid 0")
        t_wizard.refresh_from_db()
    assert t_wizard.paranoid == 0
