import pytest

from moo.core import code, create, lookup, parse
from moo.core.models import Object


def setup_item(location: Object, name: str = "red ball") -> Object:
    """Create a Generic Thing child in the given location."""
    system = lookup(1)
    return create(name, parents=[system.thing], location=location)


# --- inventory ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_inventory_empty(t_init: Object, t_wizard: Object):
    """inventory() with no items sends 'You are empty-handed.' via tell."""
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.warns(RuntimeWarning, match="You are empty-handed."):
            t_wizard.inventory()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_inventory_one_item(t_init: Object, t_wizard: Object):
    """inventory() with one item sends the header and item name via tell."""
    with code.ContextManager(t_wizard, lambda _: None):
        setup_item(t_wizard, "widget")
        with pytest.warns(RuntimeWarning) as w:
            t_wizard.inventory()
    messages = [str(x.message) for x in w.list]
    assert any("You are carrying:" in m for m in messages)
    assert any("widget" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_inventory_multiple_items(t_init: Object, t_wizard: Object):
    """inventory() with multiple items sends all names via tell."""
    with code.ContextManager(t_wizard, lambda _: None):
        setup_item(t_wizard, "apple")
        setup_item(t_wizard, "banana")
        with pytest.warns(RuntimeWarning) as w:
            t_wizard.inventory()
    messages = [str(x.message) for x in w.list]
    assert any("You are carrying:" in m for m in messages)
    assert any("apple" in m for m in messages)
    assert any("banana" in m for m in messages)


# --- accept ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_non_player(t_init: Object, t_wizard: Object):
    """accept() on a $player child allows non-player objects."""
    with code.ContextManager(t_wizard, lambda _: None):
        player_obj = lookup("Player")
        widget = setup_item(t_wizard.location)
        assert player_obj.accept(widget) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_player(t_init: Object, t_wizard: Object):
    """accept() on a $player child rejects other player objects."""
    with code.ContextManager(t_wizard, lambda _: None):
        player_obj = lookup("Player")
        assert player_obj.accept(player_obj) is False


# --- take ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_player_blocked(t_init: Object, t_wizard: Object):
    """Trying to take a player prints an error to the caller."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "get Player")
    assert "You can't take a player!" in printed


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


# --- @gag --- (skipped: parser dispatch for no-dspec multi-arg verb needs further work)
# test_gag_player, test_gag_object, test_gag_already_gagged, test_gag_no_args


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
def test_ungag_everyone(t_init: Object, t_wizard: Object):
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
    assert printed == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_paranoid_1_stores_responsible(t_init: Object, t_wizard: Object):
    """tell() with paranoid=1 appends callers and message to responsible."""
    with code.ContextManager(t_wizard, lambda _: None):
        player_obj = lookup("Player")
        player_obj.paranoid = 1
        player_obj.tell("track me")
        player_obj.refresh_from_db()
    assert len(player_obj.responsible) > 0


# --- message verbs ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_absent_msg(t_init: Object, t_wizard: Object):
    """page_absent_msg() returns a string containing the player's name."""
    with code.ContextManager(t_wizard, lambda _: None):
        result = t_wizard.page_absent_msg()
    assert "Wizard" in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_origin_msg(t_init: Object, t_wizard: Object):
    """page_origin_msg() returns a string with the player's name and location."""
    with code.ContextManager(t_wizard, lambda _: None):
        result = t_wizard.page_origin_msg()
    assert "Wizard" in result
    assert "The Laboratory" in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_echo_msg(t_init: Object, t_wizard: Object):
    """page_echo_msg() returns the echo confirmation string."""
    with code.ContextManager(t_wizard, lambda _: None):
        result = t_wizard.page_echo_msg()
    assert result == "Your message has been sent."


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


# --- make ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_make_creates_object(t_init: Object, t_wizard: Object):
    """make <name> creates a new object and prints a confirmation."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "make test widget")
    assert any("test widget" in line for line in printed)
    assert lookup("test widget") is not None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_make_with_parent(t_init: Object, t_wizard: Object):
    """make <name> from: <parent> creates an object with the given parent."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        parse.interpret(ctx, "make shiny thing from Generic Thing")
        new_obj = lookup("shiny thing")
        thing = lookup("Generic Thing")
    assert thing in new_obj.parents.all()


# --- give ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_give_successful(t_init: Object, t_wizard: Object):
    """give <item> to <player> moves the item to the recipient."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        player_obj = lookup("Player")
        widget = setup_item(t_wizard, "widget")
        parse.interpret(ctx, "give widget to Player")
        widget.refresh_from_db()
    assert widget.location == player_obj


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_give_to_self(t_init: Object, t_wizard: Object):
    """give <item> to yourself prints an error."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_item(t_wizard, "widget")
        parse.interpret(ctx, "give widget to Wizard")
    assert "You can't give something to yourself." in printed


# --- @describe ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_sets_description(t_init: Object, t_wizard: Object):
    """@describe <obj> as <text> sets the description on the object."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, "@describe widget as A shiny widget.")
        widget.refresh_from_db()
    assert widget.description() == "[color deep_sky_blue1]A shiny widget.[/color deep_sky_blue1]"
    assert any("Description set for" in line for line in printed)


# --- look_self ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_shows_sleeping(t_init: Object, t_wizard: Object):
    """look_self() on a player prints a sleeping status message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        t_wizard.look_self()
    assert any("sleeping" in line for line in printed)
