# -*- coding: utf-8 -*-
"""
Tests for moo.sdk.context helpers.
"""

import pytest

from moo.core import code, parse
from moo.sdk import invoked_verb_name


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_invoked_verb_name_returns_typed_name(t_init, t_wizard):
    """When a parser is active, returns the lowercased first word the
    player typed — even when they typed it in mixed case."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        lex = parse.Lexer("LOOK at the leaflet")
        ctx.set_parser(parse.Parser(lex, t_wizard))
        assert invoked_verb_name() == "look"
        assert invoked_verb_name("fallback") == "look"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_invoked_verb_name_returns_default_without_parser(t_init, t_wizard):
    """No active parser (async/scheduled verb invocation): falls back to default."""
    with code.ContextManager(t_wizard, lambda _: None):
        assert invoked_verb_name() is None
        assert invoked_verb_name("frobulate") == "frobulate"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_invoked_verb_name_handles_empty_words(t_init, t_wizard):
    """Parser exists but ``words`` is empty (defensive): falls back to default."""

    class _StubParser:
        words: list = []

    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        ctx.set_parser(_StubParser())
        assert invoked_verb_name("frobulate") == "frobulate"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_invoked_verb_name_lowercases(t_init, t_wizard):
    """Mixed-case input is normalised to lowercase."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        lex = parse.Lexer("FroBuLate")
        ctx.set_parser(parse.Parser(lex, t_wizard))
        assert invoked_verb_name() == "frobulate"
