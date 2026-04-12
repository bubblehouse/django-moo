"""
Integration tests for the zork1 command verbs.
"""

import pytest
from moo.core import code, parse
from moo.sdk import lookup, create


def place(obj, dest):
    """Move obj to dest via ORM (zork1 has no moveto verb)."""
    obj.location = dest
    obj.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_take_takeable_object(t_init, t_wizard):
    """Taking a takeable object moves it to inventory."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    coin = create("gold coin", parents=[lookup("Zork Thing")])
    coin.set_property("takeable", True)
    place(coin, room)

    with code.ContextManager(t_wizard, [].append) as ctx:
        parse.interpret(ctx, "take gold coin")
    coin.refresh_from_db()
    assert coin.location == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_take_nontakeable_refuses(t_init, t_wizard):
    """Taking a non-takeable object prints a refusal and leaves it in place."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    rock = create("heavy rock", parents=[lookup("Zork Thing")])
    rock.set_property("takeable", False)
    place(rock, room)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "take heavy rock")
    rock.refresh_from_db()
    assert rock.location == room
    assert any("can't take" in p.lower() for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_drop_held_object(t_init, t_wizard):
    """Dropping a held object moves it to the current room."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    coin = create("gold coin", parents=[lookup("Zork Thing")])
    coin.set_property("takeable", True)
    place(coin, t_wizard)

    with code.ContextManager(t_wizard, [].append) as ctx:
        parse.interpret(ctx, "drop gold coin")
    coin.refresh_from_db()
    assert coin.location == room


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_open_closed_container(t_init, t_wizard):
    """Opening a closed container sets the open flag."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    box = create("wooden box", parents=[lookup("Zork Container")])
    box.set_property("open", False)
    place(box, room)

    with code.ContextManager(t_wizard, [].append) as ctx:
        parse.interpret(ctx, "open wooden box")
    box.refresh_from_db()
    assert box.get_property("open") is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_close_open_container(t_init, t_wizard):
    """Closing an open container clears the open flag."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    box = create("wooden box", parents=[lookup("Zork Container")])
    box.set_property("open", True)
    place(box, room)

    with code.ContextManager(t_wizard, [].append) as ctx:
        parse.interpret(ctx, "close wooden box")
    box.refresh_from_db()
    assert box.get_property("open") is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_examine_prints_description(t_init, t_wizard):
    """Examining an object prints its description."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    coin = create("gold coin", parents=[lookup("Zork Thing")])
    coin.set_property("description", "A small gold coin.")
    place(coin, room)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "examine gold coin")
    assert any("small gold coin" in p for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_read_readable_object(t_init, t_wizard):
    """Reading a readable object prints its text property."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    leaflet = create("leaflet", parents=[lookup("Zork Thing")])
    leaflet.set_property("readable", True)
    leaflet.set_property("text", "WELCOME TO ZORK!")
    place(leaflet, room)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "read leaflet")
    assert any("WELCOME TO ZORK" in p for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_read_non_readable(t_init, t_wizard):
    """Reading a non-readable object prints a refusal."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    rock = create("heavy rock", parents=[lookup("Zork Thing")])
    rock.set_property("readable", False)
    place(rock, room)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "read heavy rock")
    assert any("nothing to read" in p.lower() for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_inventory_empty(t_init, t_wizard):
    """Empty inventory prints a message."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    for item in list(t_wizard.contents.all()):
        place(item, room)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "inventory")
    assert any("empty" in p.lower() for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_inventory_lists_items(t_init, t_wizard):
    """Inventory lists held items."""
    room = create("Test Room", parents=[lookup("Zork Room")])
    place(t_wizard, room)
    coin = create("gold coin", parents=[lookup("Zork Thing")])
    place(coin, t_wizard)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "i")
    assert any("gold coin" in p.lower() for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_score_shows_current_score(t_init, t_wizard):
    """Score command shows the player's current zstate_score and move count."""
    t_wizard.set_property("zstate_score", 35)
    t_wizard.set_property("zstate_moves", 12)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "score")
    assert any("35" in p for p in printed)
    assert any("12" in p for p in printed)
