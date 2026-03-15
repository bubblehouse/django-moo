import pytest

from moo.core import code, exceptions, parse
from moo.sdk import lookup
from moo.core.models import Object


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
def test_inventory_one_item(t_init: Object, t_wizard: Object, setup_item):
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
def test_inventory_multiple_items(t_init: Object, t_wizard: Object, setup_item):
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
def test_accept_non_player(t_init: Object, t_wizard: Object, setup_item):
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
        with pytest.warns(RuntimeWarning, match="tried unsucessfully to take you"):
            parse.interpret(ctx, "get Player")
    assert "You can't take a player!" in printed


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
def test_give_successful(t_init: Object, t_wizard: Object, setup_item):
    """give <item> to <player> moves the item to the recipient."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        player_obj = lookup("Player")
        widget = setup_item(t_wizard, "widget")
        parse.interpret(ctx, "give widget to Player")
        widget.refresh_from_db()
    assert widget.location == player_obj


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_give_to_self(t_init: Object, t_wizard: Object, setup_item):
    """give <item> to yourself prints an error."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_item(t_wizard, "widget")
        parse.interpret(ctx, "give widget to Wizard")
    assert "You can't give something to yourself." in printed


# --- @recycle ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_recycle_object(t_init: Object, t_wizard: Object, setup_item):
    """@recycle <obj> deletes the object from the database."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, "@recycle widget")
    with pytest.raises(exceptions.NoSuchObjectError):
        lookup("widget")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_recycle_no_args(t_init: Object, t_wizard: Object):
    """@recycle without an argument prints a prompt."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@recycle")
    assert any("What do you want to recycle?" in line for line in printed)
