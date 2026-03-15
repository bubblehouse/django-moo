# -*- coding: utf-8 -*-
"""
Shared helpers for moo.core tests.
"""

import types

import pytest

from .. import code


def mock_caller(is_wizard=False):
    """Minimal caller stand-in that satisfies is_wizard() checks (no DB needed)."""
    return types.SimpleNamespace(is_wizard=lambda: is_wizard)


def ctx(caller, writer=None):
    """Open a ContextManager session for the given caller."""
    return code.ContextManager(caller, writer or (lambda s: None))


def make_restricted_globals(writer):
    """Build a restricted execution globals dict for the given writer."""
    g = code.get_default_globals()
    g.update(code.get_restricted_environment("__main__", writer))
    return g


def exec_verb(src, caller=None, writer=None):
    """Run verb source in the restricted environment, return printed output."""
    caller = caller or mock_caller()
    printed = []
    with ctx(caller, printed.append):
        w = code.ContextManager.get("writer")
        code.r_exec(src, {}, make_restricted_globals(w))
    return printed


def raises_in_verb(src, exc, caller=None):
    """Assert that running src in the restricted environment raises the given exception."""
    caller = caller or mock_caller()
    with ctx(caller):
        w = code.ContextManager.get("writer")
        with pytest.raises(exc):
            code.r_exec(src, {}, make_restricted_globals(w))


def add_verb(obj, name, code_str, owner, **kwargs):
    """Create a Verb + VerbName directly via ORM, bypassing permission checks."""
    from ..models.verb import Verb, VerbName
    v = Verb.objects.create(origin=obj, owner=owner, code=code_str, **kwargs)
    VerbName.objects.create(verb=v, name=name)
    return v
