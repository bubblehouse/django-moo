import pytest

from moo.core import code, create, lookup
from moo.core.models import Object
from moo.core.parse import Lexer, Parser


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_percent_escape(t_init: Object, t_wizard: Object):
    """'%%' is replaced with a literal '%'."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("100%% done")
    assert result == "100% done"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_subjective_pronouns(t_init: Object, t_wizard: Object):
    """'%s' and '%S' are replaced with the plural subjective pronouns."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("%s said hello. %S left.")
    assert result == "they said hello. They left."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_objective_pronouns(t_init: Object, t_wizard: Object):
    """'%o' and '%O' are replaced with the plural objective pronouns."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("You see %o. You greet %O.")
    assert result == "You see them. You greet Them."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_possessive_pronouns(t_init: Object, t_wizard: Object):
    """'%p' and '%P' are replaced with the plural possessive pronouns."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("%p hat. %P coat.")
    assert result == "their hat. Their coat."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reflexive_pronouns(t_init: Object, t_wizard: Object):
    """'%r' and '%R' are replaced with the plural reflexive pronouns."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("%s hurt %r. %S hurt %R.")
    assert result == "they hurt themselves. They hurt Themselves."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_name_substitution(t_init: Object, t_wizard: Object):
    """'%n' is replaced with the player's name."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        player = lookup("Player")
        result = system.string_utils.pronoun_sub("Hello, %n!", player)
    assert result == "Hello, Player!"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_name_capitalized_substitution(t_init: Object, t_wizard: Object):
    """'%N' is replaced with the player's name."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        player = lookup("Player")
        result = system.string_utils.pronoun_sub("%N arrives.", player)
    assert result == "Player arrives."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dobj_no_parser(t_init: Object, t_wizard: Object):
    """'%d' passes through unchanged when there is no parser."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("You pick up %d.")
    assert result == "You pick up %d."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dobj_capitalized_no_parser(t_init: Object, t_wizard: Object):
    """'%D' passes through unchanged when there is no parser."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("You drop %D.")
    assert result == "You drop %D."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_pobj_no_parser(t_init: Object, t_wizard: Object):
    """'%i(prep)' passes through unchanged when there is no parser."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("You put it %i(in).")
    assert result == "You put it %i(in)."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_custom_property(t_init: Object, t_wizard: Object):
    """'%x(prop)' is replaced with the value of who's named property."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        player = lookup("Player")
        player.set_property("title", "the adventurer")
        player.save()
        result = system.string_utils.pronoun_sub("%s is known as %x(title).", player)
    assert result == "they is known as the adventurer."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_custom_property_capitalized(t_init: Object, t_wizard: Object):
    """'%X(prop)' is replaced with the property value, capitalized."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        player = lookup("Player")
        player.set_property("title", "the adventurer")
        player.save()
        result = system.string_utils.pronoun_sub("%X(title) arrives.", player)
    assert result == "The adventurer arrives."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_custom_property_missing(t_init: Object, t_wizard: Object):
    """'%x(prop)' passes through when the property does not exist."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("Has %x(nonexistent).")
    assert result == "Has %x(nonexistent)."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_unknown_code_passthrough(t_init: Object, t_wizard: Object):
    """An unrecognised '%' code is left unchanged."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("Hello %z world.")
    assert result == "Hello %z world."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_explicit_who_argument(t_init: Object, t_wizard: Object):
    """An explicit 'who' argument overrides the default player."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        player = lookup("Player")
        player.set_property("ps", "they")
        player.set_property("po", "them")
        player.save()
        result = system.string_utils.pronoun_sub("You see %s. You greet %o.", player)
    assert result == "You see they. You greet them."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_no_substitution_codes(t_init: Object, t_wizard: Object):
    """Text with no substitution codes is returned unchanged."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("Nothing to see here.")
    assert result == "Nothing to see here."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_multiple_substitutions(t_init: Object, t_wizard: Object):
    """Multiple codes in the same string are all substituted correctly."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("%S picks up the ball and throws %o at %r.")
    assert result == "They picks up the ball and throws them at themselves."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dobj_with_parser(t_init: Object, t_wizard: Object):
    """'%d' is replaced with the direct object's name when a parser is active."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        system = lookup(1)
        widget = create("widget", parents=[system.thing], location=t_wizard.location)
        parser = Parser(Lexer("take widget"), t_wizard)
        ctx.set_parser(parser)
        result = system.string_utils.pronoun_sub("You pick up %d.")
    assert result == f"You pick up {widget.title()}."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dobj_capitalized_with_parser(t_init: Object, t_wizard: Object):
    """'%D' is replaced with the direct object's name, capitalized."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        system = lookup(1)
        widget = create("widget", parents=[system.thing], location=t_wizard.location)
        parser = Parser(Lexer("take widget"), t_wizard)
        ctx.set_parser(parser)
        result = system.string_utils.pronoun_sub("%D lands in your pack.")
    assert result == f"{widget.title().capitalize()} lands in your pack."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_pobj_with_parser(t_init: Object, t_wizard: Object):
    """'%i(prep)' is replaced with the preposition object's name when a parser is active."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        system = lookup(1)
        box = create("box", parents=[system.thing], location=t_wizard.location)
        parser = Parser(Lexer("look in box"), t_wizard)
        ctx.set_parser(parser)
        result = system.string_utils.pronoun_sub("You peer %i(in).")
    assert result == f"You peer {box.title()}."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_pobj_capitalized_with_parser(t_init: Object, t_wizard: Object):
    """'%I(prep)' is replaced with the preposition object's name, capitalized."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        system = lookup(1)
        box = create("box", parents=[system.thing], location=t_wizard.location)
        parser = Parser(Lexer("look in box"), t_wizard)
        ctx.set_parser(parser)
        result = system.string_utils.pronoun_sub("%I(in) looms before you.")
    assert result == f"{box.title().capitalize()} looms before you."
