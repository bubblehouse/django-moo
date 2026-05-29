# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: restricted builtin functions.

Covers: type/__metaclass__, dir, getattr/hasattr, setattr/delattr,
callable, isinstance, dunder attribute syntax, safe_hasattr INSPECT_ATTRIBUTES
gap, AttributeError.obj disclosure, and allowed builtin return values.
"""

import sys
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
    assert printed == ["False"]


def test_hasattr_normal_names_still_work():
    """hasattr on a normal name must still work."""
    printed = exec_verb("print(hasattr('hello', 'upper'))")
    assert printed == ["True"]


# ---------------------------------------------------------------------------
# Dunder attribute syntax must remain blocked (regression guard)
# ---------------------------------------------------------------------------


def test_dunder_syntax_blocked():
    """

    Dunder attribute syntax (obj.__class__) is rejected at compile time by
    RestrictedPython and raises SyntaxError. Access is denied before execution.
    """
    raises_in_verb("x = ''.__class__", (AttributeError, TypeError, SyntaxError))


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
    assert printed == ["True"]
    printed = exec_verb("print(callable('hello'))")
    assert printed == ["False"]


def test_isinstance_accessible_but_cannot_probe_dunder_classes():
    """

    isinstance() is in safe_builtins and is used by legitimate verb code.
    Without type() or __subclasses__(), an attacker cannot navigate the class
    hierarchy.  'object' is not in the sandbox, so issubclass(str, object) raises NameError.
    """
    printed = exec_verb("print(isinstance('hi', str))")
    assert printed == ["True"]
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


# ---------------------------------------------------------------------------
# Frame/generator inspection attributes blocked by INSPECT_ATTRIBUTES (pass 15)
# ---------------------------------------------------------------------------


def test_generator_gi_frame_blocked_via_getattr():
    """

    CVE-2023-37271 style: RestrictedPython 8.1 blocks `gen.gi_frame` at
    compile time (AST transform), but `getattr(gen, 'gi_frame')` bypasses
    the AST check and goes through our runtime safe_getattr.  Since
    'gi_frame' does not start with '_', the underscore guard alone would not
    catch it.

    The INSPECT_ATTRIBUTES check in safe_getattr closes this path.  Without
    it, an attacker can capture gi_frame, walk up f_back twice to the
    do_eval() frame, access f_builtins.get('__import__') (a dict method call
    that bypasses _getitem_), and import os for a full sandbox escape.
    """
    raises_in_verb(
        "gen = (x for x in [1])\nf = getattr(gen, 'gi_frame')",
        AttributeError,
    )


def test_generator_gi_code_blocked_via_getattr():
    """getattr(gen, 'gi_code') must raise AttributeError (INSPECT_ATTRIBUTES)."""
    raises_in_verb(
        "gen = (x for x in [1])\nc = getattr(gen, 'gi_code')",
        AttributeError,
    )


def test_inspect_attributes_covers_attack_chain():
    """INSPECT_ATTRIBUTES must include all frame/generator attributes used in sandbox-escape chains."""
    from moo.core.code import INSPECT_ATTRIBUTES

    for attr in ("gi_frame", "gi_code", "f_back", "f_globals", "f_builtins", "f_locals", "tb_frame"):
        assert attr in INSPECT_ATTRIBUTES, f"{attr!r} missing from INSPECT_ATTRIBUTES"


# ---------------------------------------------------------------------------
# safe_hasattr must also check INSPECT_ATTRIBUTES
# ---------------------------------------------------------------------------


def test_safe_hasattr_does_not_leak_gi_frame():
    """

    safe_hasattr only blocked underscore-prefixed names before this fix.
    hasattr(gen, 'gi_frame') returned True even though getattr(gen, 'gi_frame')
    is blocked by INSPECT_ATTRIBUTES in safe_getattr.

    This leaks that the attribute exists — a live generator's gi_frame is
    non-None, confirming it is running.  That boolean is the first step in the
    frame-walk sandbox-escape technique: probe with hasattr, then walk frames
    to reach real builtins.

    Fix: safe_hasattr now checks INSPECT_ATTRIBUTES and returns False for any
    name in that set, matching safe_getattr's behaviour.
    """
    printed = exec_verb("gen = (x for x in [1])\nprint(hasattr(gen, 'gi_frame'))")
    assert printed == ["False"]


def test_safe_hasattr_does_not_leak_gi_code():
    """safe_hasattr returns False for 'gi_code' (in INSPECT_ATTRIBUTES)."""
    printed = exec_verb("gen = (x for x in [1])\nprint(hasattr(gen, 'gi_code'))")
    assert printed == ["False"]


def test_safe_hasattr_does_not_leak_f_locals():
    """safe_hasattr returns False for 'f_locals' (in INSPECT_ATTRIBUTES)."""
    printed = exec_verb("gen = (x for x in [1])\nprint(hasattr(gen, 'f_locals'))")
    assert printed == ["False"]


# ---------------------------------------------------------------------------
# AttributeError.obj in Python 3.12+
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.version_info < (3, 12), reason="AttributeError.obj added in Python 3.12")
def test_attribute_error_obj_returns_object_verb_already_had():
    """

    Python 3.12 added AttributeError.obj — the object on which a C-level
    attribute lookup failed.  The name 'obj' has no underscore prefix, so
    safe_getattr does not block it.

    This is safe: when verb code calls getattr(x, 'nonexistent') and it
    fails, e.obj equals x — the same reference the verb already held.  Verb
    code cannot use e.obj to gain access to objects they could not already
    reach through normal sandbox paths.

    e.name (also Python 3.12+) is a plain string — the attribute name.
    Neither attribute opens a new escalation path.
    """
    printed = exec_verb(
        "x = 'hello'\n"
        "try:\n"
        "    getattr(x, 'nonexistent_attr')\n"
        "except AttributeError as e:\n"
        "    print(e.obj is x)\n"
        "    print(e.name)\n"
    )
    assert printed == ["True", "nonexistent_attr"]


@pytest.mark.skipif(sys.version_info < (3, 12), reason="AttributeError.obj added in Python 3.12")
def test_attribute_error_obj_is_none_for_guard_raised_errors():
    """

    AttributeErrors raised by our guards (e.g. safe_getattr raising
    AttributeError('__class__')) do not set e.obj — we construct the error
    manually without specifying the object.  Only CPython's C-level
    PyObject_GetAttr sets e.obj automatically on failure.

    Manually raised guard errors therefore expose no hidden object reference.
    """
    printed = exec_verb(
        "try:\n    getattr('hello', '__class__')\nexcept AttributeError as e:\n    print(e.obj is None)\n"  # pylint: disable=implicit-str-concat
    )
    assert printed == ["True"]


# ---------------------------------------------------------------------------
# sorted / enumerate / list / set return values
# ---------------------------------------------------------------------------


def test_sorted_returns_plain_list():
    """sorted() returns a plain list — no new attack surface over list literals."""
    printed = exec_verb("print(sorted([3, 1, 2]))")
    assert printed == ["[1, 2, 3]"]


def test_enumerate_iteration_safe():
    """
    enumerate() returns an enumerate object whose __next__ and __iter__ are
    underscore-prefixed and blocked.  The idiomatic for-loop path works
    normally and yields (int, value) tuples with no dangerous attributes.
    """
    printed = exec_verb(
        "pairs = []\nfor i, v in enumerate(['a', 'b']):\n    pairs.append((i, v))\nprint(pairs)\n"  # pylint: disable=implicit-str-concat
    )
    assert printed == ["[(0, 'a'), (1, 'b')]"]


def test_enumerate_next_dunder_blocked():
    """enumerate.__next__ is underscore-prefixed and must raise AttributeError."""
    raises_in_verb(
        "e = enumerate([1])\ngetattr(e, '__next__')()",
        AttributeError,
    )


def test_set_operations_safe():
    """
    set() exposes add/remove/discard/union etc. — all return sets, integers,
    or booleans.  Adding a live object reference to a set gives no new access:
    the caller already had the reference.
    """
    printed = exec_verb(
        "s = set([1, 2, 3])\ns.add(4)\nprint(sorted(list(s)))\n"  # pylint: disable=implicit-str-concat
    )
    assert printed == ["[1, 2, 3, 4]"]


# ---------------------------------------------------------------------------
# next() return value + non-escalation (Pass 22)
# ---------------------------------------------------------------------------


def test_next_returns_safe_element():
    """
    next() returns the iterator's next yielded element.

    Attack-surface reasoning: the element type is whatever the verb's own
    iterable contains — already a sandbox-accessible object.  next() exposes no
    attribute of its own; it calls the iterator's C-level __next__, the same
    protocol a for-loop already drives via _getiter_.  Return value here is a
    plain (int, str) tuple — no chain to ORM instances or framework internals.
    """
    printed = exec_verb("print(next(enumerate(['a', 'b'])))")
    assert printed == ["(0, 'a')"]


def test_next_default_on_exhaustion():
    """next(it, default) returns the default on StopIteration — no leak, no escape."""
    printed = exec_verb("print(next(enumerate([]), 'fallback'))")
    assert printed == ["fallback"]


def test_next_on_non_iterator_raises_typeerror():
    """
    next() on a non-iterator raises TypeError — it cannot be used to coerce an
    arbitrary object into yielding internals.  Strings are iterable but are not
    iterators (no __next__), so next('hello') fails cleanly.
    """
    raises_in_verb("next('hello')", TypeError)


def test_next_does_not_expose_generator_frame():
    """
    Advancing a generator with next() yields the value, never the frame.

    Even after next(gen), the frame-walk escape stays sealed: gi_frame is in
    INSPECT_ATTRIBUTES, so getattr/hasattr both refuse it.  next() adds no path
    to gi_frame — it returns the yielded element (here, 1).
    """
    printed = exec_verb("gen = (x for x in [1, 2])\nfirst = next(gen)\nprint(first)\nprint(hasattr(gen, 'gi_frame'))\n")
    assert printed == ["1", "False"]


def test_next_generator_frame_getattr_still_blocked():
    """getattr(gen, 'gi_frame') stays blocked even when gen has been advanced by next()."""
    raises_in_verb(
        "gen = (x for x in [1, 2])\nnext(gen)\ngetattr(gen, 'gi_frame')",
        AttributeError,
    )


# ---------------------------------------------------------------------------
# iter() return value + non-escalation (Pass 22)
# ---------------------------------------------------------------------------


def test_iter_returns_iterator_over_safe_elements():
    """
    iter() returns an iterator over the supplied iterable.

    Attack-surface reasoning: iter() *is* the function bound to _getiter_, which
    RestrictedPython already calls for every for-loop and comprehension.
    Exposing it as a builtin grants no capability a for-loop doesn't already
    have.  The iterator yields the iterable's own (sandbox-accessible) elements;
    its only attributes are underscore-prefixed (__next__/__iter__), already
    blocked.
    """
    printed = exec_verb("it = iter([10, 20])\nprint(next(it))\nprint(next(it))\n")
    assert printed == ["10", "20"]


def test_iter_two_arg_callable_sentinel_bounded():
    """
    The two-arg iter(callable, sentinel) form calls a sandbox-defined callable
    until it returns the sentinel.

    The callable is verb-authored and already invocable by the verb, so calling
    it repeatedly via iter() opens no new path — it is equivalent to a while
    loop the verb could already write.  Verified bounded: the counter callable
    stops at the sentinel.
    """
    printed = exec_verb(
        "box = [0]\ndef step():\n    box[0] = box[0] + 1\n    return box[0]\nvals = list(iter(step, 3))\nprint(vals)\n"
    )
    assert printed == ["[1, 2]"]


def test_iter_dunder_next_still_blocked():
    """The iterator from iter() still hides __next__ behind the underscore guard."""
    raises_in_verb("getattr(iter([1]), '__next__')()", AttributeError)


def test_iter_does_not_expose_generator_frame():
    """
    iter(gen) returns the generator itself; gi_frame stays sealed.

    iter() introduces no generator surface that genexprs don't already create,
    and the INSPECT_ATTRIBUTES guard keeps gi_frame unreachable through both
    getattr and hasattr.
    """
    printed = exec_verb("gen = (x for x in [1])\nprint(iter(gen) is gen)\nprint(hasattr(gen, 'gi_frame'))\n")
    assert printed == ["True", "False"]
