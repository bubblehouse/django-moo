from termiverse.core.models.object import Object
from termiverse.tests import *
from termiverse.core import parse, exceptions

import pytest

@pytest.mark.django_db
def test_parse_look(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("look")
    parser = parse.Parser(lex, t_wizard)
    verb = parser.get_verb()
    names = [v['name'] for v in verb.names.values('name')]
    assert 'look' in names
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

@pytest.mark.django_db
def test_parse_look_my_bag_of_holding(t_init: Object, t_wizard: Object):
    bag = Object.objects.get(name="bag of holding")
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

@pytest.mark.django_db
def test_parse_verb_pobj(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("look through peephole")
    parser = parse.Parser(lex, t_wizard)
    assert not parser.has_dobj(), "unexpected object found for dobj"
    assert not parser.has_dobj_str(), "unexpected string found for dobj"
    assert parser.has_pobj_str('through'), "no prepositional object string found for 'through'"
    assert not parser.has_pobj('through'), "no prepositional object found for 'through'"
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj()
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_pobj("through")
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_dobj_str()
    assert parser.get_pobj_str("through") == "peephole"

@pytest.mark.django_db
def test_parse_verb_pobj_pobj(t_init: Object, t_wizard: Object):
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

@pytest.mark.django_db
def test_parse_verb_dobj_pobj(t_init: Object, t_wizard: Object):
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

@pytest.mark.django_db
def test_complex(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("@eval the wizard from 'bag under stairs' with tongs in wizard's bag")
    parser = parse.Parser(lex, t_wizard)
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_pobj("from")
    with pytest.raises(exceptions.NoSuchObjectError):
        parser.get_pobj("with")
    assert parser.get_pobj_str('from') == 'bag under stairs'
    assert parser.get_dobj() == t_wizard
    assert parser.get_pobj_str("with") == "tongs"

@pytest.mark.django_db
def test_aliases(t_init: Object, t_wizard: Object):
    alias = t_wizard.aliases.create(alias='The Wiz')
    lex = parse.Lexer("@eval the Wiz from 'bag under stairs' with tongs in wizard's bag")
    parser = parse.Parser(lex, t_wizard)
    assert parser.get_dobj() == t_wizard
    alias.delete()
    lex = parse.Lexer("@eval the Wiz from 'bag under stairs' with tongs in wizard's bag")
    parser = parse.Parser(lex, t_wizard)
    assert not parser.has_dobj()

@pytest.mark.django_db
def test_quoted_strings(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("@eval wizard to 'something here'")
    parser = parse.Parser(lex, t_wizard)
    assert parser.get_pobj_str('to') == 'something here'

@pytest.mark.django_db
def test_bug_9(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("@eval here as 'Large amounts of chalkdust lay all over the "
                       "objects in this room, and a large chalkboard at one end has "
                       "become coated with a thick layer of Queen Anne\\'s lace. "
                       "Strange semi-phosphorescant orbs are piled all around "
                       "this ancient hall.'")
    parser = parse.Parser(lex, t_wizard)
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj_str('around')
    assert "\\" not in parser.get_pobj_str('as')

@pytest.mark.django_db
def test_inventory(t_init: Object, t_wizard: Object):
    box = Object.objects.create(name='box')
    box.location = t_wizard
    box.save()
    lex = parse.Lexer("@eval my box")
    parser = parse.Parser(lex, t_wizard)
    assert parser.has_dobj()
    user = Object.objects.get(name__iexact='player')
    box.location = user
    box.save()
    lex = parse.Lexer("@eval player's box")
    parser = parse.Parser(lex, t_wizard)
    assert parser.has_dobj()