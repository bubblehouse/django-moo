# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: RestrictedPython write/read guards and string formatting.

Covers: _write_.__setitem__, _getitem_, str.format/format_map,
dict.update known gap (passes 3, 4, 5).
"""

from .utils import exec_verb, raises_in_verb


# ---------------------------------------------------------------------------
# _write_.__setitem__ must block underscore keys
# ---------------------------------------------------------------------------

def test_write_setitem_underscore_key_blocked():
    """

    obj['__class__'] = x must raise KeyError in restricted code.
    _write_.__setitem__ now checks for underscore-prefixed keys consistently
    with __setattr__.
    """
    raises_in_verb("d = dict()\nd['__class__'] = 'hacked'", KeyError)


# ---------------------------------------------------------------------------
# _getitem_ must block underscore keys (read side)
# ---------------------------------------------------------------------------

def test_getitem_underscore_key_blocked():
    """

    Reading d['__class__'] in restricted code must raise KeyError.
    dict() (a C builtin) can construct a mapping with underscore keys without
    going through _write_.__setitem__; _getitem_ must guard the read side too.
    """
    raises_in_verb("d = dict([('__class__', 'x')])\nprint(d['__class__'])", KeyError)


def test_getitem_normal_keys_still_work():
    """Normal (non-underscore) key reads must continue to work."""
    printed = exec_verb("d = dict(a=1)\nprint(d['a'])")
    assert printed == [1]


# ---------------------------------------------------------------------------
# str.format() / str.format_map() must not be accessible
# ---------------------------------------------------------------------------

def test_str_format_dunder_blocked():
    """

    str.format() is blocked to prevent C-level dunder traversal.
    '{0.__class__}'.format(obj) bypasses _getattr_ entirely because Python's
    format engine resolves attribute chains using the real C-level getattr.
    Blocking access to .format on string instances closes this vector.
    """
    raises_in_verb("print('{0.__class__}'.format('hello'))", AttributeError)


def test_str_format_map_dunder_blocked():
    """str.format_map() is blocked for the same reason as str.format()."""
    raises_in_verb("print('{key}'.format_map({'key': 'ok'}))", AttributeError)


def test_str_format_blocked_even_via_variable():
    """

    The format string can be constructed at runtime to defeat static scanning.
    The block must be on the .format attribute itself, not on the string content.
    """
    raises_in_verb("fmt = '{0.' + '__class__' + '}'\nprint(fmt.format('hello'))", AttributeError)


def test_str_format_class_method_blocked():
    """

    `str.format(template, arg)` calls format as a class-level unbound method.
    The previous guard only checked `isinstance(obj, str)`, which returns False
    when obj is the `str` type itself (a `type`, not a `str` instance).

    str.format("{0.__class__}", some_obj) resolves attribute chains via the
    C-level format engine without going through our _getattr_ hook, exposing
    protected attributes as string representations.  The guard now also checks
    `isinstance(obj, type) and issubclass(obj, str)` to close this path.
    """
    raises_in_verb("str.format('{0}', 'hello')", AttributeError)


def test_str_format_class_method_blocked_with_dunder():
    """str.format with a dunder chain in the template must also be blocked."""
    raises_in_verb("str.format('{0.__class__}', 'hello')", AttributeError)


def test_str_normal_methods_still_work():
    """Blocking .format must not affect other string methods."""
    printed = exec_verb("print('hello'.upper())")
    assert printed == ["HELLO"]
    printed = exec_verb("print('a,b'.split(','))")
    assert printed == [["a", "b"]]


def test_str_replace_still_works():
    """

    str.replace() is the safe substitution method used by message verbs.
    It must remain accessible.
    """
    printed = exec_verb("print('hello {name}'.replace('{name}', 'world'))")
    assert printed == ["hello world"]


# ---------------------------------------------------------------------------
# Known gap: dict.update() + dict.get() bypass _write_/__getitem__ guards
# ---------------------------------------------------------------------------

def test_dict_update_bypasses_write_guard():
    """

    dict.update({'__class__': x}) inserts underscore keys at C level,
    bypassing _write_.__setitem__. The key can then be retrieved via
    dict.get() or .items()/.values(), bypassing _getitem_.

    This is a known policy gap. dict subclassing would be needed to close it
    fully; for now this test documents the inconsistency.
    """
    raises_in_verb("d = {}\nd['__class__'] = 'x'", KeyError)
    printed = exec_verb("d = {}\nd.update({'__class__': 'gap'})\nprint(d.get('__class__'))")
    assert printed == ["gap"], "Known gap: dict.update() bypasses _write_.__setitem__"
