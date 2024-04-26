import logging

import pytest

from moo.core.models.object import Object
from moo.tests import *  # pylint: disable=wildcard-import
from moo.core import parse, exceptions

log = logging.getLogger(__name__)

@pytest.mark.django_db
def test_parse(t_init: Object, t_wizard: Object):
    bag = t_wizard.find('bag of holding')[0]
    bag.aliases.create(alias='bag')
    Object.objects.create(name="tongs", location=bag)
    nook = Object.objects.create(name="nook under stairs", location=t_wizard.location)
    Object.objects.create(name="bag", location=nook)

    parser = parse.Parser(
        t_wizard,
        "take the bag from 'nook under stairs' with tongs in wizard's bag"
    )
    assert parser.words._.objects == [nook, bag]

@pytest.mark.django_db
def test_parse_imperative_command(t_init: Object, t_wizard: Object):
    parser = parse.Parser(t_wizard, "look")
    verb = parser.get_verb()
    names = [v['name'] for v in verb.names.values('name')]
    assert 'look' in names
    assert not parser.has_dobj(), "unexpected object found for dobj"
    assert not parser.has_dobj_str(), "unexpected string found for dobj"
    assert not parser.prepositions, "unexpected prepositional objects found"
    with pytest.raises(Object.DoesNotExist):
        parser.get_dobj()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj("on")
    with pytest.raises(Object.DoesNotExist):
        parser.get_dobj_str()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj_str("on")

@pytest.mark.django_db
def test_parse_direct_object(t_init: Object, t_wizard: Object):
    bag = Object.objects.get(name="bag of holding")
    parser = parse.Parser(t_wizard, "look my 'bag of holding'")
    assert parser.get_dobj() == bag
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
def test_parse_object_of_the_preposition(t_init: Object, t_wizard: Object):
    parser = parse.Parser(t_wizard, "look through peephole")
    assert not parser.has_dobj(), "unexpected object found for dobj"
    assert not parser.has_dobj_str(), "unexpected string found for dobj"
    assert parser.has_pobj_str('through'), "no prepositional object string found for 'through'"
    assert not parser.has_pobj('through'), "unexpected object found for 'through'"
    with pytest.raises(Object.DoesNotExist):
        parser.get_dobj()
    with pytest.raises(Object.DoesNotExist):
        parser.get_pobj("through")
    with pytest.raises(Object.DoesNotExist):
        parser.get_dobj_str()
    assert parser.get_pobj_str("through") == "peephole"

@pytest.mark.django_db
def test_parse_object_of_the_preposition_with_preposition(t_init: Object, t_wizard: Object):
    parser = parse.Parser(t_wizard, "look through peephole with wizard")
    assert not parser.has_dobj(), "unexpected object found for dobj"
    assert not parser.has_dobj_str(), "unexpected string found for dobj"
    assert parser.get_pobj("with") == t_wizard
    assert parser.get_pobj_str("with") == "wizard"
    assert parser.get_pobj_str("through") == "peephole"
    with pytest.raises(Object.DoesNotExist):
        parser.get_dobj()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj("from")
    with pytest.raises(Object.DoesNotExist):
        parser.get_dobj_str()

@pytest.mark.django_db
def test_parse_direct_object_object_of_the_preposition_with_preposition(t_init: Object, t_wizard: Object):
    parser = parse.Parser(t_wizard, "@eval glasses from wizard with tongs")
    with pytest.raises(Object.DoesNotExist):
        parser.get_dobj()
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj("under")
    assert parser.get_dobj_str() == "glasses"
    assert parser.get_pobj_str("with") == "tongs"
    assert parser.get_pobj("from") == t_wizard
    assert parser.get_pobj_str("from") == "wizard"

@pytest.mark.django_db
def test_parse_direct_object_and_multiple_prepositions_with_specifiers(t_init: Object, t_wizard: Object):
    parser = parse.Parser(t_wizard, "@eval the wizard from 'bag under stairs' with tongs in wizard's bag")
    with pytest.raises(Object.DoesNotExist):
        parser.get_pobj("from")
    with pytest.raises(Object.DoesNotExist):
        parser.get_pobj("with")
    assert parser.get_pobj_str('from') == 'bag under stairs'
    assert parser.get_dobj() == t_wizard
    assert parser.get_pobj_str("with") == "tongs"

@pytest.mark.django_db
def test_parse_command_referring_to_aliases(t_init: Object, t_wizard: Object):
    alias = t_wizard.aliases.create(alias='The Wiz')
    parser = parse.Parser(t_wizard, "@eval the Wiz from 'bag under stairs' with tongs in wizard's bag")
    assert parser.get_dobj() == t_wizard
    alias.delete()
    parser = parse.Parser(t_wizard, "@eval the Wiz from 'bag under stairs' with tongs in wizard's bag")
    assert not parser.has_dobj()

@pytest.mark.django_db
def test_parse_with_quoted_strings(t_init: Object, t_wizard: Object):
    parser = parse.Parser(t_wizard, "@eval wizard to 'something here'")
    assert parser.get_pobj_str('to') == 'something here'

@pytest.mark.django_db
def test_parse_with_quoted_strings_and_escapes(t_init: Object, t_wizard: Object):
    parser = parse.Parser(t_wizard, "@eval here as 'Large amounts of chalkdust lay all over the "
                          "objects in this room, and a large chalkboard at one end has "
                          "become coated with a thick layer of Queen Anne\\'s lace. "
                          "Strange semi-phosphorescant orbs are piled all around "
                          "this ancient hall.'")
    with pytest.raises(exceptions.NoSuchPrepositionError):
        parser.get_pobj_str('around')
    assert "\\" not in parser.get_pobj_str('as')

@pytest.mark.django_db
def test_parse_with_my_object(t_init: Object, t_wizard: Object):
    box = Object.objects.create(name='box')
    box.location = t_wizard
    box.save()
    parser = parse.Parser(t_wizard, "@eval my box")
    assert parser.has_dobj()
    user = Object.objects.get(name__iexact='player')
    box.location = user
    box.save()
    parser = parse.Parser(t_wizard, "@eval player's box")
    assert parser.has_dobj()
