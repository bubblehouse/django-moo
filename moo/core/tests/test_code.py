# -*- coding: utf-8 -*-
"""
Comprehensive tests for moo/core/code.py

Covers:
  - ContextManager lifecycle and get()
  - ContextManager caller stack
  - ContextManager per-session caches
  - get_default_globals() and get_restricted_environment()
  - Each underscore key in the restricted environment
  - _print_ / _print mechanism (RestrictedPython print protocol)
  - compile_verb_code() and its LRU cache
  - do_eval() string path (compile_restricted) and compiled-code path
  - r_exec() / r_eval()
  - Restricted import security (allowed, forbidden, wizard-only)
"""

import types

import pytest

from moo.core.models.object import Object

from .. import code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock(is_wizard=False):
    """Minimal caller/player stand-in that satisfies is_wizard() checks."""
    return types.SimpleNamespace(is_wizard=lambda: is_wizard)


def _ctx(caller, writer=None):
    return code.ContextManager(caller, writer or (lambda s: None))


def _make_globals(writer):
    """Build a restricted execution globals dict for the given writer."""
    g = code.get_default_globals()  # pylint: disable=redefined-builtin
    g.update(code.get_restricted_environment("__main__", writer))
    return g


# ---------------------------------------------------------------------------
# Original tests (kept unchanged)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_eval_simple_command(t_init: Object, t_wizard: Object):
    def _writer(msg):
        raise RuntimeError("print was called unexpectedly")

    with code.ContextManager(t_wizard, _writer):
        writer = code.ContextManager.get("writer")
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment("__main__", writer))
        result = code.do_eval("dir()", {}, globals)
        assert result == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_trivial_printing(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        writer = code.ContextManager.get("writer")
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment("__main__", writer))
        result = code.do_eval("print('test')", {}, globals)
        assert result is None
        assert printed == ["test"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_printing_imported_caller(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        writer = code.ContextManager.get("writer")
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment("__main__", writer))
        src = "from moo.core import context\nprint(context.caller)"
        code.r_exec(src, {}, globals)
        assert printed == [t_wizard]

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_caller_stack(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        from moo.core import context, lookup, create

        player = lookup("Player")

        # Create 3 new objects to serve as verb owners
        p3 = create("TestPlayer3")
        p4 = create("TestPlayer4")
        p5 = create("TestPlayer5")

        # Build a chain of 5 verbs on the Player class, each owned by a different player.
        # add_verb() sets owner = ContextManager.get("caller") = t_wizard, so we
        # update the owner afterward. Permissions (allow "everyone" "execute") are set
        # automatically by apply_default_permissions during Verb.save() on creation.

        v1 = player.add_verb("test-caller-chain-1", code="""
from moo.core import context
this.invoke_verb("test-caller-chain-2")
""")
        v1.owner = t_wizard
        v1.save()

        v2 = player.add_verb("test-caller-chain-2", code="""
from moo.core import context
this.invoke_verb("test-caller-chain-3")
""")
        v2.owner = player
        v2.save()

        v3 = player.add_verb("test-caller-chain-3", code="""
from moo.core import context
this.invoke_verb("test-caller-chain-4")
""")
        v3.owner = p3
        v3.save()

        v4 = player.add_verb("test-caller-chain-4", code="""
from moo.core import context
this.invoke_verb("test-caller-chain-5")
""")
        v4.owner = p4
        v4.save()

        v5 = player.add_verb("test-caller-chain-5", code="""
from moo.core import context
for frame in context.caller_stack:
    print(frame)
""")
        v5.owner = p5
        v5.save()

        # Invoke the chain
        player.invoke_verb("test-caller-chain-1")

        # Stack is fully unwound after all verbs return
        assert context.caller_stack == []

        # The 5 frames were captured in order by verb 5
        assert printed == [
            dict(caller=t_wizard, origin=player, player=t_wizard, previous_caller=t_wizard, this=player, verb_name="test-caller-chain-1"),
            dict(caller=player, origin=player, player=t_wizard, previous_caller=t_wizard, this=player, verb_name="test-caller-chain-2"),
            dict(caller=p3, origin=player, player=t_wizard, previous_caller=player, this=player, verb_name="test-caller-chain-3"),
            dict(caller=p4, origin=player, player=t_wizard, previous_caller=p3, this=player, verb_name="test-caller-chain-4"),
            dict(caller=p5, origin=player, player=t_wizard, previous_caller=p4, this=player, verb_name="test-caller-chain-5"),
        ]


# ---------------------------------------------------------------------------
# 1. ContextManager – lifecycle and get()
# ---------------------------------------------------------------------------

def test_context_manager_defaults():
    caller = _mock()
    writer = lambda s: None
    with _ctx(caller, writer):
        assert code.ContextManager.get("caller") is caller
        assert code.ContextManager.get("player") is caller  # defaults to caller
        assert code.ContextManager.get("writer") is writer
        assert code.ContextManager.get("task_id") is None


def test_context_manager_player_explicit():
    caller = _mock()
    player = _mock()
    with code.ContextManager(caller, lambda s: None, player=player):
        assert code.ContextManager.get("caller") is caller
        assert code.ContextManager.get("player") is player


def test_context_manager_task_id():
    caller = _mock()
    with code.ContextManager(caller, lambda s: None, task_id="task-99"):
        assert code.ContextManager.get("task_id") == "task-99"


def test_context_manager_get_unknown_raises():
    caller = _mock()
    with _ctx(caller):
        with pytest.raises(NotImplementedError):
            code.ContextManager.get("bogus")


def test_context_manager_get_parser_default():
    caller = _mock()
    with _ctx(caller):
        assert code.ContextManager.get("parser") is None


def test_context_manager_set_parser():
    caller = _mock()
    sentinel = object()
    with _ctx(caller) as ctx:
        ctx.set_parser(sentinel)
        assert code.ContextManager.get("parser") is sentinel


def test_context_manager_is_active():
    caller = _mock()
    assert not code.ContextManager.is_active()
    with _ctx(caller):
        assert code.ContextManager.is_active()
    assert not code.ContextManager.is_active()


def test_context_manager_nested():
    outer = _mock()
    inner = _mock()
    with _ctx(outer):
        assert code.ContextManager.get("caller") is outer
        with _ctx(inner):
            assert code.ContextManager.get("caller") is inner
        assert code.ContextManager.get("caller") is outer


def test_context_manager_caller_stack_outside_session():
    # Must return [] (not the internal _UNSET sentinel) when no session is active.
    assert code.ContextManager.get("caller_stack") == []


# ---------------------------------------------------------------------------
# 2. ContextManager – caller stack
# ---------------------------------------------------------------------------

def test_context_manager_override_and_pop_caller():
    original = _mock()
    new_caller = _mock()
    with _ctx(original):
        code.ContextManager.override_caller(new_caller)
        assert code.ContextManager.get("caller") is new_caller
        assert len(code.ContextManager.get("caller_stack")) == 1

        code.ContextManager.pop_caller()
        assert code.ContextManager.get("caller") is original
        assert len(code.ContextManager.get("caller_stack")) == 0


def test_context_manager_pop_caller_empty_raises():
    caller = _mock()
    with _ctx(caller):
        with pytest.raises(RuntimeError):
            code.ContextManager.pop_caller()


def test_context_manager_override_caller_stack_contents():
    caller = _mock()
    new_caller = _mock()
    this = object()
    origin = object()
    player = _mock()
    with _ctx(caller):
        code.ContextManager.override_caller(
            new_caller,
            this=this,
            verb_name="test-verb",
            origin=origin,
            player=player,
        )
        stack = code.ContextManager.get("caller_stack")
        assert len(stack) == 1
        frame = stack[0]
        assert frame["caller"] is new_caller
        assert frame["this"] is this
        assert frame["verb_name"] == "test-verb"
        assert frame["origin"] is origin
        assert frame["player"] is player
        assert frame["previous_caller"] is caller
        code.ContextManager.pop_caller()


# ---------------------------------------------------------------------------
# 3. ContextManager – per-session caches
# ---------------------------------------------------------------------------

def test_context_manager_caches_are_dicts_inside_session():
    caller = _mock()
    with _ctx(caller):
        assert code.ContextManager.get_perm_cache() == {}
        assert code.ContextManager.get_verb_lookup_cache() == {}
        assert code.ContextManager.get_prop_lookup_cache() == {}


def test_context_manager_caches_are_none_outside_session():
    assert code.ContextManager.get_perm_cache() is None
    assert code.ContextManager.get_verb_lookup_cache() is None
    assert code.ContextManager.get_prop_lookup_cache() is None


def test_context_manager_caches_isolated_between_sessions():
    caller = _mock()
    with _ctx(caller):
        code.ContextManager.get_perm_cache()["sentinel"] = True

    # A new session must start with a fresh empty dict.
    with _ctx(caller):
        assert "sentinel" not in code.ContextManager.get_perm_cache()


# ---------------------------------------------------------------------------
# 4. get_default_globals() / get_restricted_environment()
# ---------------------------------------------------------------------------

def test_get_default_globals():
    g = code.get_default_globals()
    assert set(g.keys()) == {"__name__", "__package__", "__doc__"}
    assert g["__name__"] == "__main__"
    assert g["__package__"] is None
    assert g["__doc__"] is None


def test_get_restricted_environment_exact_keys():
    env = code.get_restricted_environment("test_verb", lambda s: None)
    expected = {
        "_apply_", "_print_", "_print", "_write_",
        "_getattr_", "_getitem_", "_getiter_", "_inplacevar_",
        "_unpack_sequence_", "_iter_unpack_sequence_",
        "__import__", "__builtins__", "__metaclass__",
        "__name__", "__package__", "__doc__", "verb_name",
    }
    assert set(env.keys()) == expected
    assert env["__name__"] == "test_verb"
    assert env["verb_name"] == "test_verb"


def test_print_and_print_factory_both_present():
    """
    RestrictedPython transforms `print(x)` into `_print_(_print)._call_print(x)`.
    Both keys must be present:
      _print_  — factory callable, receives the current collector, returns a new one
      _print   — initial collector instance; its _call_print() routes to the writer
    """
    collected = []
    env = code.get_restricted_environment("test", collected.append)

    assert "_print_" in env
    assert "_print" in env

    # Factory: callable with the current collector as arg → new object with _call_print
    new_collector = env["_print_"](env["_print"])
    assert callable(getattr(new_collector, "_call_print", None))

    # Initial collector: _call_print routes output to the writer
    env["_print"]._call_print("routed")
    assert "routed" in collected


def test_inplace_var_addition():
    env = code.get_restricted_environment("test", lambda s: None)
    assert env["_inplacevar_"]("+=", 2, 3) == 5


def test_inplace_var_unsupported_raises():
    env = code.get_restricted_environment("test", lambda s: None)
    with pytest.raises(NotImplementedError):
        env["_inplacevar_"]("-=", 5, 1)


def test_get_protected_attribute_allows_public():
    env = code.get_restricted_environment("test", lambda s: None)
    obj = types.SimpleNamespace(name="hello")
    assert env["_getattr_"](obj, "name") == "hello"


def test_get_protected_attribute_private_blocked():
    env = code.get_restricted_environment("test", lambda s: None)
    obj = types.SimpleNamespace(_secret="hidden")
    with pytest.raises(AttributeError):
        env["_getattr_"](obj, "_secret")


def test_set_protected_attribute_private_blocked():
    env = code.get_restricted_environment("test", lambda s: None)
    obj = types.SimpleNamespace()
    with pytest.raises(AttributeError):
        env["_write_"](obj)._private = "value"


def test_write_setitem_passthrough():
    env = code.get_restricted_environment("test", lambda s: None)
    d = {}
    env["_write_"](d)["key"] = "value"
    assert d["key"] == "value"


def test_apply_calls_function():
    env = code.get_restricted_environment("test", lambda s: None)
    assert env["_apply_"](len, [1, 2, 3]) == 3


def test_getitem():
    env = code.get_restricted_environment("test", lambda s: None)
    assert env["_getitem_"]([10, 20, 30], 1) == 20


def test_getiter():
    env = code.get_restricted_environment("test", lambda s: None)
    assert list(env["_getiter_"]([1, 2, 3])) == [1, 2, 3]


# ---------------------------------------------------------------------------
# 5. compile_verb_code() and LRU cache
# ---------------------------------------------------------------------------

def test_compile_verb_code_returns_object():
    result = code.compile_verb_code("pass", "<test-compile>")
    assert hasattr(result, "code")


def test_compile_verb_code_is_cached():
    a = code.compile_verb_code("x = 1", "<cache-hit>")
    b = code.compile_verb_code("x = 1", "<cache-hit>")
    assert a is b


def test_compile_verb_code_different_args():
    a = code.compile_verb_code("x = 1", "<diff-a>")
    b = code.compile_verb_code("x = 2", "<diff-b>")
    assert a is not b


# ---------------------------------------------------------------------------
# 6. do_eval() – string path (compile_restricted)
# ---------------------------------------------------------------------------

def test_do_eval_string_expression():
    g = code.get_default_globals()
    g.update(code.get_restricted_environment("__main__", lambda s: None))
    result = code.do_eval("1 + 1", {}, g, runtype="eval")
    assert result == 2


def test_do_eval_string_exec():
    g = code.get_default_globals()
    g.update(code.get_restricted_environment("__main__", lambda s: None))
    result = code.do_eval("x = 1", {}, g, runtype="exec")
    assert result is None


# ---------------------------------------------------------------------------
# 7. r_exec() / r_eval()
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_r_exec_executes_code(t_init: Object, t_wizard: Object):
    with _ctx(t_wizard):
        g = _make_globals(lambda s: None)
        code.r_exec("pass", {}, g)  # must not raise


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_r_eval_returns_value(t_init: Object, t_wizard: Object):
    with _ctx(t_wizard):
        g = _make_globals(lambda s: None)
        # r_eval wraps code in a function body, so a return is needed to get a value.
        result = code.r_eval("return 1 + 2", {}, g)
        assert result == 3


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_r_exec_print_calls_writer(t_init: Object, t_wizard: Object):
    printed = []
    with _ctx(t_wizard, printed.append):
        g = _make_globals(printed.append)
        code.r_exec("print('hello')", {}, g)
    assert "hello" in printed


# ---------------------------------------------------------------------------
# 8. Restricted import security
# ---------------------------------------------------------------------------

def test_restricted_import_allowed_module():
    # 're' is in ALLOWED_MODULES — any caller may import it.
    with _ctx(_mock(is_wizard=False)):
        env = code.get_restricted_environment("test", lambda s: None)
        import re as re_module
        result = env["__import__"]("re", {}, {}, [], 0)
        assert result is re_module


def test_restricted_import_forbidden_module():
    with _ctx(_mock(is_wizard=False)):
        env = code.get_restricted_environment("test", lambda s: None)
        with pytest.raises(ImportError):
            env["__import__"]("os", {}, {}, [], -1)


def test_restricted_import_wizard_module_as_wizard():
    # 'moo.core.models.object' is in WIZARD_ALLOWED_MODULES.
    # __import__("a.b.c") with empty fromlist returns the top-level package;
    # we just verify the call succeeds without ImportError.
    with _ctx(_mock(is_wizard=True)):
        env = code.get_restricted_environment("test", lambda s: None)
        env["__import__"]("moo.core.models.object", {}, {}, [], 0)  # must not raise


def test_restricted_import_wizard_module_as_non_wizard():
    with _ctx(_mock(is_wizard=False)):
        env = code.get_restricted_environment("test", lambda s: None)
        with pytest.raises(ImportError):
            env["__import__"]("moo.core.models.object", {}, {}, [], 0)
