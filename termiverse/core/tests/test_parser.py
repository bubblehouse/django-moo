from termiverse.core.models.object import Object
from termiverse.tests import *
from termiverse.core import parse

import pytest

@pytest.mark.django_db
def test_parse_look(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("look")
    parser = parse.Parser(lex, t_wizard)
    verb = parser.get_verb()
    names = [v['name'] for v in verb.names.values('name')]
    assert 'look' in names
    assert parser.dobj is None

@pytest.mark.django_db
def test_parse_look_my_bag_of_holding(t_init: Object, t_wizard: Object):
    bag = Object.objects.get(name="bag of holding")
    lex = parse.Lexer("look my bag of holding")
    parser = parse.Parser(lex, t_wizard)
    assert parser.dobj == bag
