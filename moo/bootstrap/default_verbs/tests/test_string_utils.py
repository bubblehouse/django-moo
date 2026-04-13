import pytest

from moo.core import code
from moo.sdk import create, lookup
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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_this_no_parser(t_init: Object, t_wizard: Object):
    """'%t' passes through unchanged when there is no parser."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("You see %t.")
    assert result == "You see %t."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_this_capitalized_no_parser(t_init: Object, t_wizard: Object):
    """'%T' passes through unchanged when there is no parser."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.pronoun_sub("%T glows faintly.")
    assert result == "%T glows faintly."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_this_with_parser(t_init: Object, t_wizard: Object):
    """'%t' is replaced with this object's name when a parser is active."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        system = lookup(1)
        torch = create("torch", parents=[system.thing], location=t_wizard.location)
        parser = Parser(Lexer("take torch"), t_wizard)
        parser.this = torch
        ctx.set_parser(parser)
        result = system.string_utils.pronoun_sub("You pick up %t.")
    assert result == f"You pick up {torch.title()}."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_this_capitalized_with_parser(t_init: Object, t_wizard: Object):
    """'%T' is replaced with this object's name, capitalized."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        system = lookup(1)
        torch = create("torch", parents=[system.thing], location=t_wizard.location)
        parser = Parser(Lexer("take torch"), t_wizard)
        parser.this = torch
        ctx.set_parser(parser)
        result = system.string_utils.pronoun_sub("%T illuminates the room.")
    assert result == f"{torch.title().capitalize()} illuminates the room."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_plain_short_string(t_init: Object, t_wizard: Object):
    """A string already under 80 chars with no newlines is returned unchanged."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.rewrap("Hello, world.")
    assert result == "Hello, world."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_collapses_single_newline(t_init: Object, t_wizard: Object):
    """A single newline within a paragraph is replaced with a space."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.rewrap("Line one\nLine two")
    assert result == "Line one Line two"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_preserves_double_newline(t_init: Object, t_wizard: Object):
    """Double newlines between paragraphs are preserved as paragraph breaks."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.rewrap("Para one.\n\nPara two.")
    assert result == "Para one.\n\nPara two."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_preserves_triple_newline_as_paragraph(t_init: Object, t_wizard: Object):
    """Three or more consecutive newlines collapse to a single paragraph break."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.rewrap("Para one.\n\n\nPara two.")
    assert result == "Para one.\n\nPara two."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_wraps_long_line(t_init: Object, t_wizard: Object):
    """A line exceeding 80 characters is broken at a word boundary."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        long_line = "word " * 20  # 100 characters
        result = system.string_utils.rewrap(long_line.strip())
    for line in result.split("\n"):
        assert len(line) <= 80


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_replaces_tabs(t_init: Object, t_wizard: Object):
    """Tab characters are replaced with a space."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.rewrap("Hello\tworld.")
    assert result == "Hello world."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_replaces_carriage_return(t_init: Object, t_wizard: Object):
    """CRLF line endings are normalised before processing."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.rewrap("Line one\r\nLine two")
    assert result == "Line one Line two"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_collapses_multiple_spaces(t_init: Object, t_wizard: Object):
    """Multiple consecutive spaces are collapsed to one."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        result = system.string_utils.rewrap("Too   many    spaces.")
    assert result == "Too many spaces."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_multiline_paragraph_with_wrap(t_init: Object, t_wizard: Object):
    """A multi-line paragraph with embedded newlines is reflowed and wrapped correctly."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        text = (
            "A cavernous laboratory filled with gadgetry of every kind,\n"
            "this seems like a dumping ground for every piece of dusty forgotten\n"
            "equipment a mad scientist might require."
        )
        result = system.string_utils.rewrap(text)
    # Should be one paragraph, each line <= 80 chars
    assert "\n\n" not in result
    for line in result.split("\n"):
        assert len(line) <= 80
    assert "cavernous laboratory" in result
    assert "mad scientist" in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rewrap_two_paragraphs_each_wrapped(t_init: Object, t_wizard: Object):
    """Two paragraphs are each wrapped independently and separated by a blank line."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        text = ("word " * 20).strip() + "\n\n" + ("other " * 20).strip()
        result = system.string_utils.rewrap(text)
    parts = result.split("\n\n")
    assert len(parts) == 2
    for part in parts:
        for line in part.split("\n"):
            assert len(line) <= 80


# --- english_list ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_empty(t_init: Object, t_wizard: Object):
    """english_list([]) returns an empty string."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.english_list([])
    assert result == ""


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_one(t_init: Object, t_wizard: Object):
    """english_list(["a"]) returns the single item."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.english_list(["apple"])
    assert result == "apple"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_two(t_init: Object, t_wizard: Object):
    """english_list(["a", "b"]) returns 'a and b'."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.english_list(["cats", "dogs"])
    assert result == "cats and dogs"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_three(t_init: Object, t_wizard: Object):
    """english_list(["a", "b", "c"]) returns 'a, b, and c'."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.english_list(["red", "green", "blue"])
    assert result == "red, green, and blue"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_four(t_init: Object, t_wizard: Object):
    """english_list with four items uses Oxford comma."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.english_list(["a", "b", "c", "d"])
    assert result == "a, b, c, and d"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_object_consonant(t_init: Object, t_wizard: Object):
    """Non-player Object items are prefixed with 'a' when the name starts with a consonant."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        thing = create("newspaper", parents=[system.thing])
        result = system.string_utils.english_list([thing])
    assert result == "a newspaper"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_object_vowel(t_init: Object, t_wizard: Object):
    """Non-player Object items are prefixed with 'an' when the name starts with a vowel."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        thing = create("orange", parents=[system.thing])
        result = system.string_utils.english_list([thing])
    assert result == "an orange"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_object_player(t_init: Object, t_wizard: Object):
    """Player Object items render as their title with no article."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.english_list([t_wizard])
    assert result == "Wizard"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_english_list_mixed_objects_and_strings(t_init: Object, t_wizard: Object):
    """A mixed list of Objects and strings renders each appropriately."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        thing = create("newspaper", parents=[system.thing])
        result = system.string_utils.english_list([thing, "something"])
    assert result == "a newspaper and something"


# --- match_string ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_string_prefix(t_init: Object, t_wizard: Object):
    """match_string returns candidates whose prefix matches the query."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.match_string("sw", ["sword", "shield", "axe"])
    assert result == ["sword"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_string_multiple(t_init: Object, t_wizard: Object):
    """match_string returns all matching candidates."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.match_string("s", ["sword", "shield", "axe"])
    assert result == ["sword", "shield"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_string_no_match(t_init: Object, t_wizard: Object):
    """match_string returns empty list when nothing matches."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.match_string("z", ["sword", "shield"])
    assert result == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_string_case_insensitive(t_init: Object, t_wizard: Object):
    """match_string is case-insensitive."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.string_utils.match_string("SW", ["Sword", "Shield", "Axe"])
    assert result == ["Sword"]
