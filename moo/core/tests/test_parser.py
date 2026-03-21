import pytest

from moo.core import exceptions, parse
from moo.core.models.object import Object


def test_lex_imperative_command():
    lex = parse.Lexer("look")
    assert lex.command == "look"


def test_lex_direct_object():
    lex = parse.Lexer("look here")
    assert lex.dobj_str == "here"


def test_lex_object_of_the_preposition():
    lex = parse.Lexer("look at this")
    assert lex.prepositions["at"][0][1] == "this"


def test_lex_direct_object_with_preposition():
    lex = parse.Lexer("look at painting with the glasses")
    assert lex.prepositions["at"][0][1] == "painting"
    assert lex.prepositions["with"][0][0] == "the"
    assert lex.prepositions["with"][0][1] == "glasses"


def test_lex_look_at_QUOTED_painting_with_the_glasses():
    lex = parse.Lexer("look at 'painting with the glasses'")
    assert lex.prepositions["at"][0][1] == "painting with the glasses"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_imperative_command(t_init: Object, t_wizard: Object):
    t_wizard.add_verb("look", code="pass")
    lex = parse.Lexer("look")
    parser = parse.Parser(lex, t_wizard)
    verb = parser.get_verb()
    names = [v["name"] for v in verb.names.values("name")]
    assert "look" in names
    assert not parser.has_dobj(), "unexpected object found for dobj"
    assert not parser.has_dobj_str(), "unexpected string found for dobj"
    assert not parser.prepositions, "unexpected prepositional objects found"
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj("on")
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj_str()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj_str("on")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_direct_object(t_init: Object, t_wizard: Object):
    bag = Object.objects.create(name="bag of holding", location=t_wizard)
    lex = parse.Lexer("look my bag of holding")
    parser = parse.Parser(lex, t_wizard)
    assert parser.dobj == bag
    assert parser.has_dobj(), "dobj 'my bag of holding' not found"
    assert parser.has_dobj_str(), "dobj string 'my bag of holding' not found"
    assert not parser.prepositions, "unexpected prepositional objects/strings found"
    assert parser.get_dobj() == bag
    assert parser.get_dobj_str().lower() == bag.name.lower()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj("on")
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj_str("on")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_object_of_the_preposition(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("look through peephole")
    parser = parse.Parser(lex, t_wizard)
    assert not parser.has_dobj(), "unexpected object found for dobj"
    assert not parser.has_dobj_str(), "unexpected string found for dobj"
    assert parser.has_pobj_str("through"), "no prepositional object string found for 'through'"
    assert not parser.has_pobj("through"), "no prepositional object found for 'through'"
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj()
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_pobj("through")
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj_str()
    assert parser.get_pobj_str("through") == "peephole"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_object_of_the_preposition_with_preposition(t_init: Object, t_wizard: Object):
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    lex = parse.Lexer("look through peephole with wizard")
    parser = parse.Parser(lex, t_wizard)
    assert not parser.has_dobj(), "unexpected object found for dobj"
    assert not parser.has_dobj_str(), "unexpected string found for dobj"
    assert parser.get_pobj("with") == t_wizard
    assert parser.get_pobj_str("with") == "wizard"
    assert parser.get_pobj_str("through") == "peephole"
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj("from")
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj_str()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_direct_object_object_of_the_preposition_with_preposition(t_init: Object, t_wizard: Object):
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    lex = parse.Lexer("@eval glasses from wizard with tongs")
    parser = parse.Parser(lex, t_wizard)
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj("under")
    assert parser.get_dobj_str() == "glasses"
    assert parser.get_pobj_str("with") == "tongs"
    assert parser.get_pobj("from") == t_wizard
    assert parser.get_pobj_str("from") == "wizard"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_direct_object_and_multiple_prepositions_with_specifiers(t_init: Object, t_wizard: Object):
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    lex = parse.Lexer("@eval the wizard from 'bag under stairs' with tongs in wizard's bag")
    parser = parse.Parser(lex, t_wizard)
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_pobj("from")
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_pobj("with")
    assert parser.get_pobj_str("from") == "bag under stairs"
    assert parser.get_dobj() == t_wizard
    assert parser.get_pobj_str("with") == "tongs"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_command_referring_to_aliases(t_init: Object, t_wizard: Object):
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    alias = t_wizard.aliases.create(alias="The Wiz")
    lex = parse.Lexer("@eval the Wiz from 'bag under stairs' with tongs in wizard's bag")
    parser = parse.Parser(lex, t_wizard)
    assert parser.get_dobj() == t_wizard
    alias.delete()
    lex = parse.Lexer("@eval the Wiz from 'bag under stairs' with tongs in wizard's bag")
    parser = parse.Parser(lex, t_wizard)
    assert not parser.has_dobj()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_with_quoted_strings(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("@eval wizard to 'something here'")
    parser = parse.Parser(lex, t_wizard)
    assert parser.get_pobj_str("to") == "something here"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_specifier(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("make a jar")
    parser = parse.Parser(lex, t_wizard)
    assert parser.get_dobj_str() == "jar"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_with_quoted_strings_and_escapes(t_init: Object, t_wizard: Object):
    lex = parse.Lexer(
        "@eval here as 'Large amounts of chalkdust lay all over the "
        "objects in this room, and a large chalkboard at one end has "
        "become coated with a thick layer of Queen Anne\\'s lace. "
        "Strange semi-phosphorescant orbs are piled all around "
        "this ancient hall.'"
    )
    parser = parse.Parser(lex, t_wizard)
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj_str("around")
    assert "\\" not in parser.get_pobj_str("as")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_double_quoted_string_with_escaped_inner_quotes(t_init: Object, t_wizard: Object):
    # Strings ending with \" were previously corrupted by strip() removing
    # the inner quote char from the end along with the outer closing quote.
    lex = parse.Lexer('@describe #1 as "Top reads \\"Homer J.\\""')
    parser = parse.Parser(lex, t_wizard)
    result = parser.get_pobj_str("as")
    assert result == 'Top reads "Homer J."'
    assert not result.endswith("\\")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_double_quoted_string_with_inner_escaped_quotes(t_init: Object, t_wizard: Object):
    lex = parse.Lexer('@describe #1 as "He said \\"hello\\""')
    parser = parse.Parser(lex, t_wizard)
    result = parser.get_pobj_str("as")
    assert result == 'He said "hello"'


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_with_my_object(t_init: Object, t_wizard: Object):
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    box = Object.objects.create(name="box")
    box.location = t_wizard
    box.save()
    lex = parse.Lexer("@eval my box")
    parser = parse.Parser(lex, t_wizard)
    assert parser.has_dobj()
    user = Object.objects.create(name="player")
    user.add_verb("accept", code="return True")
    user.location = room
    user.save()
    box.location = user
    box.save()
    lex = parse.Lexer("@eval player's box")
    parser = parse.Parser(lex, t_wizard)
    assert parser.has_dobj()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_with_complex_name(t_init: Object, t_wizard: Object):
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    box = Object.objects.create(name="box containing spaces")
    box.location = t_wizard.location
    box.save()
    lex = parse.Lexer("@eval box containing spaces")
    parser = parse.Parser(lex, t_wizard)
    assert parser.get_dobj_str() == "box containing spaces"
    assert parser.get_dobj() == box


def test_lex_synonym_preposition_normalized():
    # "using" is a synonym for "with"; the Lexer should store it under the canonical key "with"
    lex = parse.Lexer("take hammer using tongs")
    assert "with" in lex.prepositions
    assert "using" not in lex.prepositions
    assert lex.prepositions["with"][0][1] == "tongs"


def test_lex_canonical_preposition_unchanged():
    # "with" is already canonical; it should still be stored as "with"
    lex = parse.Lexer("take hammer with tongs")
    assert "with" in lex.prepositions
    assert lex.prepositions["with"][0][1] == "tongs"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_synonym_get_pobj_str(t_init: object, t_wizard: object):
    # typed "using" (synonym); canonical lookup "with" should succeed
    lex = parse.Lexer("take hammer using tongs")
    parser = parse.Parser(lex, t_wizard)
    assert parser.get_pobj_str("with") == "tongs"
    # also works when calling with the synonym itself
    assert parser.get_pobj_str("using") == "tongs"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_synonym_has_pobj_str(t_init: object, t_wizard: object):
    lex = parse.Lexer("take hammer using tongs")
    parser = parse.Parser(lex, t_wizard)
    assert parser.has_pobj_str("with")
    assert parser.has_pobj_str("using")
    # non-synonym should still be False
    assert not parser.has_pobj_str("at")


def test_expand_wildcard():
    from moo.core import utils

    assert utils.expand_wildcard("describe") == ["describe"]
    assert utils.expand_wildcard("desc*ribe") == ["desc", "descr", "descri", "describ", "describe"]
    assert utils.expand_wildcard("l*ook") == ["l", "lo", "loo", "look"]
    assert utils.expand_wildcard("l**k") == ["l", "l*", "l*k"]
