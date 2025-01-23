from moo.core import parse


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
