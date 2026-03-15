# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: restricted builtin functions.

Covers: type/__metaclass__, dir, getattr/hasattr, setattr/delattr,
callable, isinstance, and dunder attribute syntax (passes 1, 2, 14).
"""

import types

import pytest

from .. import code
from .utils import ctx, exec_verb, mock_caller, raises_in_verb


# ---------------------------------------------------------------------------
# __metaclass__ must not expose type
# ---------------------------------------------------------------------------

def test_metaclass_not_in_globals():
    """__metaclass__ was a Python 2 artifact; it must not appear in the sandbox globals."""
    caller = mock_caller()
    with ctx(caller):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        assert "__metaclass__" not in g


# ---------------------------------------------------------------------------
# dir() must not be available
# ---------------------------------------------------------------------------

def test_dir_builtin_removed():
    """dir() is not in ALLOWED_BUILTINS and must raise NameError in verb code."""
    raises_in_verb("dir()", NameError)


# ---------------------------------------------------------------------------
# getattr() / hasattr() must not allow underscore names
# ---------------------------------------------------------------------------

def test_getattr_underscore_blocked():
    """getattr(obj, '__class__') must raise AttributeError, not return the class."""
    raises_in_verb("getattr('hello', '__class__')", AttributeError)


def test_getattr_normal_names_still_work():
    """getattr on a normal (non-underscore) name must still work."""
    printed = exec_verb("print(getattr('hello', 'upper')())")
    assert printed == ["HELLO"]


def test_hasattr_underscore_returns_false():
    """hasattr(obj, '__class__') must return False, not True."""
    printed = exec_verb("print(hasattr('hello', '__class__'))")
    assert printed == [False]


def test_hasattr_normal_names_still_work():
    """hasattr on a normal name must still work."""
    printed = exec_verb("print(hasattr('hello', 'upper'))")
    assert printed == [True]


# ---------------------------------------------------------------------------
# Dunder attribute syntax must remain blocked (regression guard)
# ---------------------------------------------------------------------------

def test_dunder_syntax_blocked():
    """

    Dunder attribute syntax (obj.__class__) is rejected at compile time by
    RestrictedPython — code.code is None, so exec raises TypeError.
    Either way, access is denied.
    """
    raises_in_verb("x = ''.__class__", (AttributeError, TypeError))


# ---------------------------------------------------------------------------
# setattr() / delattr() builtins must not bypass _write_ guards (pass 14)
# ---------------------------------------------------------------------------

def test_setattr_builtin_blocks_write_to_objects():
    """

    safe_builtins includes guarded_setattr from RestrictedPython.  It routes
    through full_write_guard, which wraps objects that lack _guarded_writes in
    a Wrapper that raises TypeError for any attribute write.
    """
    caller = mock_caller()
    ns = types.SimpleNamespace(x=1)
    with ctx(caller):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["obj"] = ns
        with pytest.raises(TypeError):
            code.r_exec("setattr(obj, 'y', 99)", {}, g)
    assert not hasattr(ns, "y")


def test_setattr_builtin_blocks_underscore_write():
    """

    guarded_setattr from RestrictedPython blocks ALL writes to objects that lack
    _guarded_writes, including underscore-prefixed names.
    """
    caller = mock_caller()
    ns = types.SimpleNamespace()
    with ctx(caller):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["obj"] = ns
        with pytest.raises(TypeError):
            code.r_exec("setattr(obj, '_private', 'hacked')", {}, g)
    assert not hasattr(ns, "_private")


def test_delattr_builtin_blocks_delete_on_objects():
    """

    safe_builtins includes guarded_delattr from RestrictedPython.  Like setattr,
    it routes through full_write_guard and raises TypeError for model instances.
    """
    caller = mock_caller()
    ns = types.SimpleNamespace(x=1)
    with ctx(caller):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["obj"] = ns
        with pytest.raises(TypeError):
            code.r_exec("delattr(obj, 'x')", {}, g)
    assert hasattr(ns, "x")


# ---------------------------------------------------------------------------
# callable() / isinstance() — pass 14
# ---------------------------------------------------------------------------

def test_callable_builtin_accessible_but_harmless():
    """

    callable() is in safe_builtins.  It returns True/False and cannot be used
    to call anything — it is a read-only probe.
    """
    printed = exec_verb("print(callable(print))")
    assert printed == [True]
    printed = exec_verb("print(callable('hello'))")
    assert printed == [False]


def test_isinstance_accessible_but_cannot_probe_dunder_classes():
    """

    isinstance() is in safe_builtins and is used by legitimate verb code.
    Without type() or __subclasses__(), an attacker cannot navigate the class
    hierarchy.  'object' is not in the sandbox, so issubclass(str, object) raises NameError.
    """
    printed = exec_verb("print(isinstance('hi', str))")
    assert printed == [True]
    raises_in_verb("issubclass(str, object)", NameError)


# ---------------------------------------------------------------------------
# Exception dunder attributes blocked by underscore guard (pass 14)
# ---------------------------------------------------------------------------

def test_exception_traceback_blocked_by_underscore_guard():
    """

    Exception objects have __traceback__, __context__, and __cause__ attributes
    that could expose frame references.  All are dunder-prefixed, so
    safe_getattr blocks them with AttributeError.
    """
    raises_in_verb(
        "try:\n    x = 1/0\nexcept Exception as e:\n    tb = getattr(e, '__traceback__')",
        AttributeError,
    )
    raises_in_verb(
        "try:\n    x = 1/0\nexcept Exception as e:\n    ctx = getattr(e, '__context__')",
        AttributeError,
    )
