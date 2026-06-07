# -*- coding: utf-8 -*-
"""
Development support resources for MOO programs
"""

import contextvars
import functools
import logging
import time
import warnings
from typing import Any
from collections import namedtuple
from types import ModuleType

from django.conf import settings
from django.db.models import Model
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet

from RestrictedPython import compile_restricted, compile_restricted_function
from RestrictedPython.Guards import guarded_iter_unpack_sequence, guarded_unpack_sequence, safe_builtins
from RestrictedPython.transformer import INSPECT_ATTRIBUTES

# Read-only QuerySet/Manager methods that verb code may legitimately call.
# Everything else — including all mutation methods, async variants (adelete,
# aupdate, acreate, …), and any future Django additions — is blocked by default.
_QUERYSET_ALLOWED = frozenset(
    {
        "all",
        "filter",
        "exclude",
        "first",
        "last",
        "get",
        "exists",
        "count",
        "contains",
        "order_by",
        "distinct",
        "none",
        "select_related",
        "prefetch_related",
    }
)

# Methods/properties on sandbox models whose READ requires the caller to
# hold "read" on the instance (enforced by guard_read_attribute). Field and
# reverse-relation names are NOT listed here — they are derived from
# Model._meta in _sandbox_registry(), so new fields are read-checked
# automatically. test_security_attribute_coverage.py asserts every public
# attribute on the models is classified in exactly one of these buckets.
SANDBOX_READ_METHODS: dict[str, frozenset] = {
    "object": frozenset(
        {
            "kind",
            "placement",
            "is_player",
            "is_wizard",
            "is_connected",
            "is_named",
            "find",
            "is_placed",
            "is_hidden_placement",
            "contains",
            "is_a",
            "get_ancestors",
            "get_descendents",
            "get_contents",
            "has_verb",
            "get_verb",
            "has_property",
            "get_property",
            "get_property_objects",
        }
    ),
    "verb": frozenset({"kind", "is_ability", "is_method", "annotated", "name"}),
    "property": frozenset({"kind"}),
}

# Methods exempt from the blanket read check: each performs its own
# finer-grained ACL enforcement (write/grant/entrust) or returns only
# booleans derived from the caller's own permissions.
SANDBOX_EXEMPT_METHODS: dict[str, frozenset] = {
    "object": frozenset(
        {
            "add_verb",
            "set_property",
            "add_parent",
            "remove_parent",
            "add_alias",
            "invoke_verb",
            "set_placement",
            "clear_placement",
            "save",
            "delete",
            "owns",
            "is_allowed",
            "allow",
            "deny",
            "can_caller",
            "caller_can_read",
        }
    ),
    "verb": frozenset(
        {"save", "delete", "reload", "is_bound", "passthrough", "allow", "deny", "can_caller", "caller_can_read"}
    ),
    "property": frozenset({"save", "delete", "allow", "deny", "can_caller", "caller_can_read"}),
}

# Attribute names with bespoke handling in guard_read_attribute:
# "acl" is checked with "grant" permission, before the per-kind read sets.
SANDBOX_SPECIAL_ATTRIBUTES = frozenset({"acl"})


def derive_sandbox_field_names(model) -> frozenset:
    """
    All field, FK-attname, and reverse-accessor names on *model* whose read
    requires the "read" permission. ``pk`` is added explicitly (it is a Model
    property, not in _meta.get_fields()). Underscore-prefixed names are
    excluded because the sandbox blocks all underscore reads; ``acl`` is
    excluded — it is grant-checked separately.
    """
    names = {"pk"}
    for f in model._meta.get_fields():  # pylint: disable=protected-access
        if f.auto_created and not f.concrete:
            # Reverse relation: the attribute on the instance is the accessor
            # name (related_name), not f.name. Hidden ("+") relations have none.
            accessor = f.get_accessor_name()
            if accessor:
                names.add(accessor)
            continue
        names.add(f.name)
        attname = getattr(f, "attname", None)
        if attname:
            names.add(attname)
        if getattr(f, "choices", None):
            # Django adds get_<field>_display() for choice fields; it reads
            # the field value, so it gets the same read check.
            names.add("get_%s_display" % f.name)
    return frozenset(n for n in names if not n.startswith("_") and n not in SANDBOX_SPECIAL_ATTRIBUTES)


@functools.lru_cache(maxsize=None)
def _sandbox_registry():
    """
    Memoized sandbox model registry. Models are imported lazily here —
    moo/core/models/acl.py imports this module at import time, so code.py can
    never import models at module scope. get_restricted_environment() runs
    once per task; this makes the imports and set construction once-per-process.
    """
    from types import SimpleNamespace  # pylint: disable=import-outside-toplevel

    from moo.core.models.acl import Access, AccessibleMixin, Permission  # pylint: disable=import-outside-toplevel
    from moo.core.models.object import Alias, Object  # pylint: disable=import-outside-toplevel
    from moo.core.models.property import Property  # pylint: disable=import-outside-toplevel
    from moo.core.models.verb import (  # pylint: disable=import-outside-toplevel
        Preposition,
        PrepositionName,
        PrepositionSpecifier,
        Repository,
        Verb,
        VerbName,
    )

    return SimpleNamespace(
        AccessibleMixin=AccessibleMixin,
        Object=Object,
        Verb=Verb,
        Property=Property,
        Alias=Alias,
        VerbName=VerbName,
        sandbox_model_types=(
            Object,
            Verb,
            Property,
            Alias,
            VerbName,
            Preposition,
            PrepositionName,
            PrepositionSpecifier,
            Repository,
            Access,
            Permission,
        ),
        object_read_attributes=derive_sandbox_field_names(Object) | SANDBOX_READ_METHODS["object"],
        verb_read_attributes=derive_sandbox_field_names(Verb) | SANDBOX_READ_METHODS["verb"],
        property_read_attributes=derive_sandbox_field_names(Property) | SANDBOX_READ_METHODS["property"],
    )


log = logging.getLogger(__name__)

TaskTime = namedtuple("TaskTime", ["elapsed", "time_limit", "remaining"])


def interpret(source, name, *args, runtype="exec", **kwargs):
    from . import context

    globals = get_default_globals()  # pylint: disable=redefined-builtin
    globals.update(get_restricted_environment(name, context.writer))
    if runtype == "exec":
        return r_exec(source, {}, globals, *args, **kwargs)
    else:
        return r_eval(source, {}, globals, *args, **kwargs)


@functools.lru_cache(maxsize=512)
def _cached_compile(body, filename):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=SyntaxWarning)
        return compile_restricted_function(
            p="this=None, passthrough=None, _=None, *args, **kwargs",
            body=body,
            name="verb",
            filename=filename,
        )


def compile_verb_code(body, filename):
    """
    Take a given piece of verb code and wrap it in a function.

    Raises SyntaxError if RestrictedPython rejects the code (restricted
    construct, underscore-aliased import, etc.). The error messages from
    the compiler are included so the caller can report them to the user.
    """
    result = _cached_compile(body, filename)
    if result.code is None or result.errors:
        msgs = "; ".join(result.errors) if result.errors else "compilation failed"
        raise SyntaxError(msgs)
    return result


def r_eval(src, locals, globals, *args, filename="<string>", **kwargs):  # pylint: disable=redefined-builtin
    code = compile_verb_code(src, filename)
    return do_eval(code, locals, globals, *args, filename=filename, runtype="eval", **kwargs)


def r_exec(src, locals, globals, *args, filename="<string>", **kwargs):  # pylint: disable=redefined-builtin
    code = compile_verb_code(src, filename)
    return do_eval(code, locals, globals, *args, filename=filename, runtype="exec", **kwargs)


def do_eval(code, locals, globals, *args, filename="<string>", runtype="eval", **kwargs):  # pylint: disable=redefined-builtin
    """
    Execute an expression in the provided environment.

    Flushes the sandbox print collector on return so any trailing
    ``print(..., end="")`` fragment reaches the writer instead of being
    discarded with the verb's globals.
    """
    collector = globals.get("_print")
    try:
        if isinstance(code, str):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SyntaxWarning)
                code = compile_restricted(code, filename, runtype)

            value = eval(code, globals, locals)  # pylint: disable=eval-used
        else:
            exec(code.code, globals, locals)  # pylint: disable=exec-used
            compiled_function = locals["verb"]
            value = compiled_function(*args, **kwargs)
        return value
    finally:
        if collector is not None:
            collector._flush()  # pylint: disable=protected-access


def get_default_globals():
    return {"__name__": "__main__", "__package__": None, "__doc__": None}


def get_restricted_environment(name, writer):
    """
    Construct an environment dictionary.
    """
    reg = _sandbox_registry()
    AccessibleMixin = reg.AccessibleMixin
    Object, Verb, Property = reg.Object, reg.Verb, reg.Property
    Alias, VerbName = reg.Alias, reg.VerbName
    sandbox_model_types = reg.sandbox_model_types
    object_read_attributes = reg.object_read_attributes
    verb_read_attributes = reg.verb_read_attributes
    property_read_attributes = reg.property_read_attributes

    def caller_is_wizard():
        caller = ContextManager.get("caller")
        return bool(caller and caller.is_wizard())

    def is_sandbox_model_class(model):
        try:
            return issubclass(model, sandbox_model_types)
        except TypeError:
            return False

    def guard_result(result):
        if isinstance(result, (QuerySet, BaseManager)):
            model = getattr(result, "model", None)
            if model is not None and not is_sandbox_model_class(model) and not caller_is_wizard():
                raise AttributeError(getattr(model, "__name__", "model"))
        if isinstance(result, Model) and not is_sandbox_model_class(type(result)) and not caller_is_wizard():
            raise AttributeError(type(result).__name__)
        return result

    def guard_read_attribute(obj, attr_name):
        caller = ContextManager.get("caller")
        if caller is None:
            return
        if attr_name == "acl" and isinstance(obj, AccessibleMixin):
            obj.can_caller("grant", obj)
        elif isinstance(obj, Object) and attr_name in object_read_attributes:
            obj.can_caller("read", obj)
        elif isinstance(obj, Verb) and attr_name in verb_read_attributes:
            obj.can_caller("read", obj)
        elif isinstance(obj, Property) and attr_name in property_read_attributes:
            obj.can_caller("read", obj)
        elif isinstance(obj, Alias):
            obj.object.can_caller("read", obj.object)
        elif isinstance(obj, VerbName):
            obj.verb.can_caller("read", obj.verb)

    def _render_print_arg(value):
        # Third-party models can't override __str__ for redaction the way
        # Object/Verb/Property do, so restricted instances render as a
        # placeholder for non-wizards. Top-level args only: ``print([key])``
        # (container repr), f-strings, and ``",".join(...)`` still hit the
        # native __str__/__repr__ — known residual gaps.
        if isinstance(value, (QuerySet, BaseManager)):
            model = getattr(value, "model", None)
            if model is not None and not is_sandbox_model_class(model) and not caller_is_wizard():
                return "<%s queryset (restricted)>" % getattr(model, "__name__", "model")
        if isinstance(value, Model) and not is_sandbox_model_class(type(value)) and not caller_is_wizard():
            return "<%s (restricted)>" % type(value).__name__
        return str(value)

    class _print_:
        # Stdlib-compatible defaults: ``print("x")`` ends with ``\n``,
        # ``print("x", end="")`` does not.  The shell writer is a println —
        # one call per writer entry, with its own trailing ``\n`` added —
        # so we buffer until a print's ``end`` carries us across a newline,
        # then emit one writer call with the trailing ``\n`` stripped
        # (writer adds it back).  Embedded newlines in args are preserved
        # verbatim so multi-line text reaches the writer as one call.
        def __init__(self):
            self._buffer = ""

        def _call_print(self, *args, sep=" ", end="\n"):
            self._buffer += sep.join(_render_print_arg(a) for a in args) + end
            if self._buffer.endswith("\n"):
                writer(self._buffer[:-1])
                self._buffer = ""

        def _flush(self):
            if self._buffer:
                writer(self._buffer)
                self._buffer = ""

    class _write_:
        def __init__(self, obj):
            object.__setattr__(self, "obj", obj)

        def __setattr__(self, name, value):
            """
            Private attribute protection using is_frame_access_allowed()
            """
            set_protected_attribute(self.obj, name, value)  # pylint: disable=no-member

        def __setitem__(self, key, value):
            """
            Passthrough property access, with underscore key protection.
            """
            if isinstance(key, str) and key.startswith("_"):
                raise KeyError(key)
            self.obj[key] = value  # pylint: disable=no-member

    def restricted_import(name, gdict, ldict, fromlist, level=-1):
        """
        Used to drastically limit the importable modules.
        """
        if name in settings.ALLOWED_MODULES:
            blocked = settings.BLOCKED_IMPORTS.get(name, set())
            if fromlist:
                for item in fromlist:
                    if item in blocked:
                        raise ImportError("Restricted: cannot import %s from %s" % (item, name))
            return __builtins__["__import__"](name, gdict, ldict, fromlist, level)
        caller = ContextManager.get("caller")
        if name in settings.WIZARD_ALLOWED_MODULES and caller and caller.is_wizard():
            return __builtins__["__import__"](name, gdict, ldict, fromlist, level)
        raise ImportError("Restricted: %s" % name)

    def validate_attribute_request(obj, attr_name):
        if isinstance(attr_name, str) and attr_name.startswith("_"):
            raise AttributeError(attr_name)
        if isinstance(attr_name, str) and attr_name in INSPECT_ATTRIBUTES:
            raise AttributeError(attr_name)
        if attr_name in ("format", "format_map") and (
            isinstance(obj, str) or (isinstance(obj, type) and issubclass(obj, str))
        ):
            raise AttributeError(attr_name)
        if isinstance(obj, Model) and not is_sandbox_model_class(type(obj)) and not caller_is_wizard():
            raise AttributeError(attr_name)
        if isinstance(obj, (QuerySet, BaseManager)):
            guard_result(obj)
            if attr_name not in _QUERYSET_ALLOWED:
                raise AttributeError(attr_name)

    def get_protected_attribute(obj, name, g=getattr):
        validate_attribute_request(obj, name)
        if isinstance(obj, ModuleType):
            module_name = getattr(obj, "__name__", "")
            if name in settings.BLOCKED_IMPORTS.get(module_name, set()):
                raise AttributeError(name)
            result = g(obj, name)
            if isinstance(result, ModuleType):
                result_name = getattr(result, "__name__", "")
                if result_name not in settings.ALLOWED_MODULES and result_name not in settings.WIZARD_ALLOWED_MODULES:
                    raise AttributeError(name)
            return guard_result(result)
        guard_read_attribute(obj, name)
        return guard_result(g(obj, name))

    def set_protected_attribute(obj, name, value, s=setattr):
        if name.startswith("_"):
            raise AttributeError(name)
        if isinstance(obj, Model) and not is_sandbox_model_class(type(obj)) and not caller_is_wizard():
            raise AttributeError(name)
        if isinstance(obj, AccessibleMixin):
            obj.can_caller("write", obj)
        return s(obj, name, value)

    def guarded_getitem(obj, key):
        if isinstance(key, str) and key.startswith("_"):
            raise KeyError(key)
        return guard_result(obj[key])

    def guarded_iter(obj):
        # Eager: reject restricted QuerySets/Managers/instances before any
        # item flows; then guard each yielded item so a plain container of
        # restricted model rows can't leak instances either.
        guard_result(obj)

        # N (spec 200): charge each yielded item against the per-task tick
        # budget so a runaway loop aborts before the Celery wall-clock kill.
        # Budget and counter are read once per iterator; the loop only mutates
        # counter[0], keeping per-item overhead to an int increment + compare.
        budget = getattr(settings, "MOO_TICK_BUDGET", 0)
        counter = _CONTEXT_VARS["tick_counter"].get() if budget else None

        def _guarded_items():
            for item in obj:
                if counter is not None:
                    counter[0] += 1
                    if counter[0] > budget:
                        from .exceptions import TickLimitError  # pylint: disable=import-outside-toplevel

                        raise TickLimitError(f"Verb exceeded the tick budget ({budget} loop iterations).")
                yield guard_result(item)

        return _guarded_items()

    def inplace_var_modification(operator, a, b):
        if operator == "+=":
            return a + b
        raise NotImplementedError("In-place modification with %s not supported." % operator)

    def safe_getattr(obj, name, *args):
        validate_attribute_request(obj, name)
        if isinstance(obj, ModuleType):
            module_name = getattr(obj, "__name__", "")
            if name in settings.BLOCKED_IMPORTS.get(module_name, set()):
                raise AttributeError(name)
            result = getattr(obj, name, *args) if args else getattr(obj, name)
            if isinstance(result, ModuleType):
                result_name = getattr(result, "__name__", "")
                if result_name not in settings.ALLOWED_MODULES and result_name not in settings.WIZARD_ALLOWED_MODULES:
                    raise AttributeError(name)
            return guard_result(result)
        guard_read_attribute(obj, name)
        return guard_result(getattr(obj, name, *args) if args else getattr(obj, name))

    def safe_hasattr(obj, name):
        try:
            safe_getattr(obj, name)
        except (AttributeError, PermissionError):
            return False
        return True

    restricted_builtins = dict(safe_builtins)
    restricted_builtins["__import__"] = restricted_import

    for n in settings.ALLOWED_BUILTINS:
        restricted_builtins[n] = __builtins__[n]
    restricted_builtins["getattr"] = safe_getattr
    restricted_builtins["hasattr"] = safe_hasattr

    _print_collector = _print_()
    env = dict(
        _apply_=lambda f, *a, **kw: f(*a, **kw),
        # RestrictedPython transforms ``print(x)`` into
        # ``_print_(_print)._call_print(x)``.  Return the same collector
        # instance every time so its buffer persists across calls and
        # ``print(..., end="")`` can coalesce fragments into one writer
        # call.  The ``x`` arg (the current collector) is intentionally
        # ignored — we already own it.
        _print_=lambda x: _print_collector,
        _print=_print_collector,
        _write_=_write_,
        _getattr_=get_protected_attribute,
        _getitem_=guarded_getitem,
        _getiter_=guarded_iter,
        _inplacevar_=inplace_var_modification,
        _unpack_sequence_=guarded_unpack_sequence,
        _iter_unpack_sequence_=guarded_iter_unpack_sequence,
        __import__=restricted_import,
        __builtins__=restricted_builtins,
        __name__=name,
        __package__=None,
        __doc__=None,
        verb_name=name,
    )

    return env


# A sentinel object (not a mutable default like []) so we can reliably detect whether
# a ContextManager is active: _CONTEXT_VARS["caller_stack"].get() is _UNSET means no
# session. Using a mutable list as the default would cause shared-state bugs — any code
# that appended to it outside a context would mutate the single default object permanently.
_UNSET = object()

# Registry mapping context-variable names to their ContextVar instances.
# To add a new context variable: add it here AND set its initial value in
# ContextManager.__init__._initial_values.  No other boilerplate required.
_CONTEXT_VARS: dict[str, contextvars.ContextVar] = {
    "caller": contextvars.ContextVar("active_caller", default=None),
    "player": contextvars.ContextVar("active_player", default=None),
    "writer": contextvars.ContextVar("active_writer", default=None),
    "parser": contextvars.ContextVar("active_parser", default=None),
    "task_id": contextvars.ContextVar("active_task_id", default=None),
    "connection": contextvars.ContextVar("active_connection", default=None),
    "start_time": contextvars.ContextVar("active_start_time", default=None),
    "caller_stack": contextvars.ContextVar("active_caller_stack", default=_UNSET),
    "perm_cache": contextvars.ContextVar("perm_cache", default=None),
    "verb_lookup_cache": contextvars.ContextVar("verb_lookup_cache", default=None),
    "prop_lookup_cache": contextvars.ContextVar("prop_lookup_cache", default=None),
    # Generic per-task scratch dict for transient state that must be shared
    # across the verb calls within a single command/invocation but never
    # persisted. Lifecycle matches the caches above (fresh per session, reset
    # on __exit__). Game-neutral: callers namespace their own keys.
    "scratch": contextvars.ContextVar("scratch", default=None),
    # When set to a list by parse_command, _publish_to_player appends each
    # published event type so the shell can read what events to expect.
    # Default None means "not tracking" — most sessions don't need this.
    "published_events": contextvars.ContextVar("published_events", default=None),
    "site": contextvars.ContextVar("site", default=None),
    # N (spec 200): per-task loop/tick counter. A single-element list so the
    # hot path mutates ``counter[0]`` in place rather than doing a contextvar
    # set per iteration. Fresh per session, reset on __exit__.
    "tick_counter": contextvars.ContextVar("tick_counter", default=None),
}


class ContextManager:
    """
    The ContextManager class is what holds critical per-execution information such as
    the active user and writer.  It uses contextvars to maintain this information across
    asynchronous calls.

    This contextmanager should really only be used once per top-level request, such as
    when a user invokes a verb or issues a command in the console. Nested uses of this
    contextmanager are supported for unit testing purposes, since eager Celery execution
    means that verb invocations within verbs happen synchronously.
    """

    @classmethod
    def get(cls, name):
        if name == "task_time":
            from celery import current_app

            start = _CONTEXT_VARS["start_time"].get()
            if start is None:
                return None
            elapsed = time.monotonic() - start
            limit = current_app.conf.task_time_limit
            remaining = (limit - elapsed) if limit is not None else None
            return TaskTime(elapsed=elapsed, time_limit=limit, remaining=remaining)
        if name == "caller_stack":
            stack = _CONTEXT_VARS["caller_stack"].get()
            # Return a copy so callers cannot mutate the live stack.
            return [] if stack is _UNSET else list(stack)
        if name in _CONTEXT_VARS:
            return _CONTEXT_VARS[name].get()
        raise NotImplementedError(f"Unknown ContextManager variable: {name}")

    @classmethod
    def get_site(cls):
        return _CONTEXT_VARS["site"].get()

    @classmethod
    def set_site(cls, site):
        _CONTEXT_VARS["site"].set(site)

    @classmethod
    def get_perm_cache(cls) -> dict | None:
        return cls.get("perm_cache")

    @classmethod
    def get_verb_lookup_cache(cls) -> dict | None:
        return cls.get("verb_lookup_cache")

    @classmethod
    def get_prop_lookup_cache(cls) -> dict | None:
        return cls.get("prop_lookup_cache")

    @classmethod
    def get_scratch(cls) -> dict | None:
        """Per-task scratch dict for transient cross-verb state (see ``scratch``
        in ``_CONTEXT_VARS``). ``None`` outside an active session."""
        return cls.get("scratch")

    @classmethod
    def is_active(cls):
        # True only when __enter__ has been called and __exit__ has not yet run.
        # Verb.__call__ uses this to skip stack tracking for utility verb calls
        # that happen outside any user session (e.g. apply_default_permissions).
        return _CONTEXT_VARS["caller_stack"].get() is not _UNSET

    @classmethod
    def override_caller(cls, caller, this=None, verb_name=None, origin=None, player=None):
        attributes = {
            "this": this,
            "verb_name": verb_name,
            "caller": caller,
            "origin": origin,
            "player": player,
            "previous_caller": _CONTEXT_VARS["caller"].get(),
        }
        _CONTEXT_VARS["caller"].set(caller)
        caller_stack = _CONTEXT_VARS["caller_stack"].get()
        caller_stack.append(attributes)
        _CONTEXT_VARS["caller_stack"].set(caller_stack)

    @classmethod
    def pop_caller(cls):
        caller_stack = _CONTEXT_VARS["caller_stack"].get()
        if not caller_stack:
            raise RuntimeError("Caller stack is empty.")
        frame = caller_stack.pop()
        _CONTEXT_VARS["caller_stack"].set(caller_stack)
        _CONTEXT_VARS["caller"].set(frame["previous_caller"])

    def __init__(
        self,
        caller: Any,
        writer: Any,
        task_id: Any = None,
        player: Any = None,
        connection: Any = None,
        track_events: bool = False,
        site: Any = None,
    ) -> None:
        self._tokens: dict = {}
        self._initial_values: dict = {
            "caller": caller,
            "player": player if player is not None else caller,
            "writer": writer,
            "parser": None,
            "task_id": task_id,
            "connection": connection,
            "start_time": time.monotonic(),
            # Fresh list per instance so each session has its own isolated stack.
            # Replacing _UNSET with a real list marks the session as active (is_active() → True)
            # and gives override_caller a mutable list to append to.
            "caller_stack": [],
            # Fresh dicts per instance for per-session caching.
            "perm_cache": {},
            "verb_lookup_cache": {},
            "prop_lookup_cache": {},
            "scratch": {},
            "published_events": [] if track_events else None,
            "site": site,
            "tick_counter": [0],
        }

    def set_parser(self, parser):
        self._initial_values["parser"] = parser
        self._tokens["parser"] = _CONTEXT_VARS["parser"].set(parser)

    def __enter__(self):
        for name, var in _CONTEXT_VARS.items():
            self._tokens[name] = var.set(self._initial_values[name])
        return self

    def __exit__(self, cls, value, traceback):
        for name, token in self._tokens.items():
            if token:
                # reset() restores to whatever the var held before __enter__'s set() call,
                # regardless of how many times override_caller/pop_caller mutated it since.
                _CONTEXT_VARS[name].reset(token)
        self._tokens.clear()
