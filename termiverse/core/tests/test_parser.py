from termiverse.core.models.object import Object
from termiverse.tests import *
from termiverse.core import parse

import pytest

@pytest.mark.django_db
def test_parse_look(t_init: Object, t_wizard: Object):
    lex = parse.Lexer("look my bag of holding")
    parser = parse.Parser(lex, t_wizard)
    verb = parser.get_verb()
    names = [v['name'] for v in verb.names.values('name')]
    assert 'look' in names
