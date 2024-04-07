import pytest

from moo.core.models.object import Object
from moo.tests import *  # pylint: disable=wildcard-import
from moo.core import parse

@pytest.mark.django_db

@pytest.mark.django_db
def test_lex_imperative_command(t_init: Object, t_wizard: Object):
    lex = parse.Parser(t_wizard, "look")
    assert lex.command == "look"

@pytest.mark.django_db
def test_lex_direct_object(t_init: Object, t_wizard: Object):
    lex = parse.Parser(t_wizard, "look here")
    assert lex.dobj_str == "here"

@pytest.mark.django_db
def test_lex_object_of_the_preposition(t_init: Object, t_wizard: Object):
    lex = parse.Parser(t_wizard, "look at this")
    assert lex.prepositions["at"] == "this"

@pytest.mark.django_db
def test_lex_direct_object_with_preposition(t_init: Object, t_wizard: Object):
    lex = parse.Parser(t_wizard, "look at painting with the glasses")
    assert lex.prepositions["at"] == "painting"
    assert lex.prepositions["with"] == "the"
    assert lex.prepositions["with"] == "glasses"

@pytest.mark.django_db
def test_lex_look_at_QUOTED_painting_with_the_glasses(t_init: Object, t_wizard: Object):
    lex = parse.Parser(t_wizard, "look at 'painting with the glasses'")
    assert lex.prepositions["at"] == "painting with the glasses"
