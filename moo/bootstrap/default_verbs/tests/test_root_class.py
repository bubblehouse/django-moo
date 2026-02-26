import pytest

from moo.core import code, create, exceptions, lookup, parse
from moo.core.models import Object
from moo.core.models.property import Property


def setup_obj(t_wizard: Object):
    """Create a plain root_class child object in the wizard's current location."""
    system = lookup(1)
    return create("test object", parents=[system.root_class], location=t_wizard.location)


# --- title ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_title_returns_name(t_init: Object, t_wizard: Object):
    """title() returns the object's name."""
    with code.ContextManager(t_wizard, lambda msg: None):
        obj = setup_obj(t_wizard)
        assert obj.title() == "test object"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_titlec_capitalizes_name(t_init: Object, t_wizard: Object):
    """titlec() returns the object's name with the first letter capitalised."""
    with code.ContextManager(t_wizard, lambda msg: None):
        obj = setup_obj(t_wizard)
        assert obj.titlec() == "Test object"


# --- description / describe / look_self ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_description_with_property(t_init: Object, t_wizard: Object):
    """description() returns a rich-formatted description string."""
    with code.ContextManager(t_wizard, lambda msg: None):
        obj = setup_obj(t_wizard)
        obj.describe("A shiny golden coin.")
        assert obj.description() == "[color deep_sky_blue1]A shiny golden coin.[/color deep_sky_blue1]"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_description_without_property(t_init: Object, t_wizard: Object):
    """description() returns a fallback string when no description property exists."""
    with code.ContextManager(t_wizard, lambda msg: None):
        obj = setup_obj(t_wizard)
        Property.objects.filter(origin=obj, name="description").delete()
        assert obj.description() == "[color deep_pink4 bold]Not much to see here.[/color deep_pink4 bold]"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_delegates_to_description(t_init: Object, t_wizard: Object):
    """look_self() prints the same output as description()."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        obj = setup_obj(t_wizard)
        obj.describe("A view from the top.")
        obj.look_self()
        assert printed == [obj.description()]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_sets_description_property(t_init: Object, t_wizard: Object):
    """describe() stores the given string as the object's description property."""
    with code.ContextManager(t_wizard, lambda msg: None):
        obj = setup_obj(t_wizard)
        obj.describe("A custom description.")
        assert obj.get_property("description") == "A custom description."


# --- accept ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_returns_false(t_init: Object, t_wizard: Object):
    """accept() returns False, preventing anything from being moved inside."""
    with code.ContextManager(t_wizard, lambda msg: None):
        obj = setup_obj(t_wizard)
        other = setup_obj(t_wizard)
        assert obj.accept(other) is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_false_blocks_movement(t_init: Object, t_wizard: Object):
    """Moving an object into a root_class child raises PermissionError."""
    with code.ContextManager(t_wizard, lambda msg: None):
        container = setup_obj(t_wizard)
        item = setup_obj(t_wizard)
        with pytest.raises(PermissionError):
            item.moveto(container)


# --- tell / tell_lines ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_sends_message_to_player(t_init: Object, t_wizard: Object):
    """tell() issues a write() for each arg when the object is a player."""
    with code.ContextManager(t_wizard, lambda msg: None):
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            t_wizard.tell("Hello, wizard!")
        messages = [str(warning.message) for warning in w.list]
        assert any("Hello, wizard!" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_non_player_does_nothing(t_init: Object, t_wizard: Object):
    """tell() has no effect when the object is not a player."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        obj = setup_obj(t_wizard)
        obj.tell("This message should be dropped.")
    assert not printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_lines_sends_each_string(t_init: Object, t_wizard: Object):
    """tell_lines() delivers every string in the list via tell()."""
    with code.ContextManager(t_wizard, lambda msg: None):
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            t_wizard.tell_lines(["first line", "second line", "third line"])
        messages = [str(warning.message) for warning in w.list]
        assert any("first line" in m for m in messages)
        assert any("second line" in m for m in messages)
        assert any("third line" in m for m in messages)


# --- eject ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eject_non_player_moves_to_none(t_init: Object, t_wizard: Object):
    """eject() moves a non-player contained object to location None."""
    with code.ContextManager(t_wizard, lambda msg: None):
        lab = t_wizard.location
        item = setup_obj(t_wizard)  # item starts in lab
        lab.eject(item)
        item.refresh_from_db()
        assert item.location is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eject_not_contained_prints_error(t_init: Object, t_wizard: Object):
    """eject() prints an error when the target object is not inside the container."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        lab = t_wizard.location
        item = create("foreign item", parents=[lookup(1).root_class], location=None)
        lab.eject(item)
        assert printed == [f"{lab.name} does not contain {item.name}."]


# --- moveto ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_moveto_changes_location(t_init: Object, t_wizard: Object):
    """moveto() relocates the object to the given destination."""
    with code.ContextManager(t_wizard, lambda msg: None):
        rooms = lookup("Generic Room")
        destination = create("Destination Room", parents=[rooms], location=None)
        item = setup_obj(t_wizard)
        item.moveto(destination)
        item.refresh_from_db()
        assert item.location == destination


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_moveto_none_clears_location(t_init: Object, t_wizard: Object):
    """moveto(None) removes the object from any location."""
    with code.ContextManager(t_wizard, lambda msg: None):
        item = setup_obj(t_wizard)
        item.moveto(None)
        item.refresh_from_db()
        assert item.location is None


# --- match ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_finds_object_by_name(t_init: Object, t_wizard: Object):
    """match() returns the object in contents whose name matches."""
    with code.ContextManager(t_wizard, lambda msg: None):
        lab = t_wizard.location
        coin = create("shiny coin", parents=[lookup(1).root_class], location=lab)
        result = lab.match("shiny coin")
        assert result == coin


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_raises_does_not_exist(t_init: Object, t_wizard: Object):
    """match() raises Object.DoesNotExist when no matching object is found."""
    with code.ContextManager(t_wizard, lambda msg: None):
        lab = t_wizard.location
        with pytest.raises(Object.DoesNotExist):
            lab.match("nonexistent thing")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_raises_ambiguous_on_duplicate_names(t_init: Object, t_wizard: Object):
    """match() raises AmbiguousObjectError when multiple contents share a name."""
    with code.ContextManager(t_wizard, lambda msg: None):
        lab = t_wizard.location
        create("duplicate coin", parents=[lookup(1).root_class], location=lab)
        create("duplicate coin", parents=[lookup(1).root_class], location=lab)
        with pytest.raises(exceptions.AmbiguousObjectError):
            lab.match("duplicate coin")


# --- is_unlocked_for ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_is_unlocked_for_no_key(t_init: Object, t_wizard: Object):
    """is_unlocked_for() returns True when the object's key property is None."""
    with code.ContextManager(t_wizard, lambda msg: None):
        obj = setup_obj(t_wizard)
        assert obj.is_unlocked_for(t_wizard) is True


# --- set_name ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_name_renames_object(t_init: Object, t_wizard: Object):
    """set_name() updates the object's name and returns True."""
    with code.ContextManager(t_wizard, lambda msg: None):
        obj = setup_obj(t_wizard)
        result = obj.set_name("renamed object")
        obj.refresh_from_db()
        assert result is True
        assert obj.name == "renamed object"


# --- examine ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_examine_prints_owner_info(t_init: Object, t_wizard: Object):
    """examine prints the object's name, id, and owner."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = setup_obj(t_wizard)
        parse.interpret(ctx, "examine test object")
        assert any(f"{obj.name} (#{obj.id} )" in line for line in printed)
        assert any(f"{obj.owner.name} (#{obj.owner.id})" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_examine_shows_description(t_init: Object, t_wizard: Object):
    """examine includes the object's description in its output."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = setup_obj(t_wizard)
        obj.describe("A golden goblet encrusted with jewels.")
        parse.interpret(ctx, "examine test object")
        assert any("golden goblet" in line for line in printed)


# --- recycle ---

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_recycle_does_nothing(t_init: Object, t_wizard: Object):
    """recycle() completes without error and leaves the object unchanged."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        obj = setup_obj(t_wizard)
        obj.recycle()
        obj.refresh_from_db()
        assert obj.name == "test object"
        assert not printed
