# -*- coding: utf-8 -*-
"""
Development support resources for MOO programs
"""

import contextvars
import functools
import logging
import warnings
from types import ModuleType

from django.conf import settings
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet

from RestrictedPython import compile_restricted, compile_restricted_function
from RestrictedPython.Guards import (guarded_iter_unpack_sequence,
                                     guarded_unpack_sequence, safe_builtins)
from RestrictedPython.transformer import INSPECT_ATTRIBUTES

# Read-only QuerySet/Manager methods that verb code may legitimately call.
# Everything else — including all mutation methods, async variants (adelete,
# aupdate, acreate, …), and any future Django additions — is blocked by default.
_QUERYSET_ALLOWED = frozenset({
    "all", "filter", "exclude",
    "first", "last", "get",
    "exists", "count", "contains",
    "order_by", "distinct", "none",
    "select_related", "prefetch_related",
})

log = logging.getLogger(__name__)


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
    """
    return _cached_compile(body, filename)


def r_eval(src, locals, globals, *args, filename="<string>", **kwargs):  # pylint: disable=redefined-builtin
    code = compile_verb_code(src, filename)
    return do_eval(code, locals, globals, *args, filename=filename, runtype="eval", **kwargs)


def r_exec(src, locals, globals, *args, filename="<string>", **kwargs):  # pylint: disable=redefined-builtin
    code = compile_verb_code(src, filename)
    return do_eval(code, locals, globals, *args, filename=filename, runtype="exec", **kwargs)


def do_eval(
    code, locals, globals, *args, filename="<string>", runtype="eval", **kwargs
):  # pylint: disable=redefined-builtin
    """
    Execute an expression in the provided environment.
    """
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


def get_default_globals():
    return {"__name__": "__main__", "__package__": None, "__doc__": None}


def get_restricted_environment(name, writer):
    """
    Construct an environment dictionary.
    """
    from moo.core.models.acl import AccessibleMixin
    from moo.core.models.property import Property

    class _print_:
        def _call_print(self, s):
            writer(s)

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

    def get_protected_attribute(obj, name, g=getattr):
        if name.startswith("_"):
            raise AttributeError(name)
        if name in INSPECT_ATTRIBUTES:
            raise AttributeError(name)
        if name in ("format", "format_map") and (
            isinstance(obj, str) or (isinstance(obj, type) and issubclass(obj, str))
        ):
            raise AttributeError(name)
        if isinstance(obj, (QuerySet, BaseManager)) and name not in _QUERYSET_ALLOWED:
            raise AttributeError(name)
        if isinstance(obj, ModuleType):
            module_name = getattr(obj, "__name__", "")
            if name in settings.BLOCKED_IMPORTS.get(module_name, set()):
                raise AttributeError(name)
            result = g(obj, name)
            if isinstance(result, ModuleType):
                result_name = getattr(result, "__name__", "")
                if (result_name not in settings.ALLOWED_MODULES
                        and result_name not in settings.WIZARD_ALLOWED_MODULES):
                    raise AttributeError(name)
            return result
        if name == "acl" and isinstance(obj, AccessibleMixin):
            caller = ContextManager.get("caller")
            if caller is not None:
                obj.can_caller("grant", obj)
        if name == "value" and isinstance(obj, Property):
            caller = ContextManager.get("caller")
            if caller is not None:
                obj.origin.can_caller("read", obj)
        return g(obj, name)

    def set_protected_attribute(obj, name, value, s=setattr):
        if name.startswith("_"):
            raise AttributeError(name)
        if isinstance(obj, AccessibleMixin):
            obj.can_caller("write", obj)
        return s(obj, name, value)

    def guarded_getitem(obj, key):
        if isinstance(key, str) and key.startswith("_"):
            raise KeyError(key)
        return obj[key]

    def inplace_var_modification(operator, a, b):
        if operator == "+=":
            return a + b
        raise NotImplementedError("In-place modification with %s not supported." % operator)

    def safe_getattr(obj, name, *args):
        if isinstance(name, str) and name.startswith("_"):
            raise AttributeError(name)
        if isinstance(name, str) and name in INSPECT_ATTRIBUTES:
            raise AttributeError(name)
        if name in ("format", "format_map") and (
            isinstance(obj, str) or (isinstance(obj, type) and issubclass(obj, str))
        ):
            raise AttributeError(name)
        if isinstance(obj, (QuerySet, BaseManager)) and name not in _QUERYSET_ALLOWED:
            raise AttributeError(name)
        if isinstance(obj, ModuleType):
            module_name = getattr(obj, "__name__", "")
            if name in settings.BLOCKED_IMPORTS.get(module_name, set()):
                raise AttributeError(name)
            result = getattr(obj, name, *args) if args else getattr(obj, name)
            if isinstance(result, ModuleType):
                result_name = getattr(result, "__name__", "")
                if (result_name not in settings.ALLOWED_MODULES
                        and result_name not in settings.WIZARD_ALLOWED_MODULES):
                    raise AttributeError(name)
            return result
        if name == "acl" and isinstance(obj, AccessibleMixin):
            caller = ContextManager.get("caller")
            if caller is not None:
                obj.can_caller("grant", obj)
        if name == "value" and isinstance(obj, Property):
            caller = ContextManager.get("caller")
            if caller is not None:
                obj.origin.can_caller("read", obj)
        return getattr(obj, name, *args) if args else getattr(obj, name)

    def safe_hasattr(obj, name):
        if isinstance(name, str) and name.startswith("_"):
            return False
        return hasattr(obj, name)

    restricted_builtins = dict(safe_builtins)
    restricted_builtins["__import__"] = restricted_import

    for n in settings.ALLOWED_BUILTINS:
        restricted_builtins[n] = __builtins__[n]
    restricted_builtins["getattr"] = safe_getattr
    restricted_builtins["hasattr"] = safe_hasattr
    env = dict(
        _apply_=lambda f, *a, **kw: f(*a, **kw),
        _print_=lambda x: _print_(),
        _print=_print_(),
        _write_=_write_,
        _getattr_=get_protected_attribute,
        _getitem_=guarded_getitem,
        _getiter_=iter,
        _inplacevar_=inplace_var_modification,
        _unpack_sequence_=guarded_unpack_sequence,
        _iter_unpack_sequence_=guarded_iter_unpack_sequence,
        __import__=restricted_import,
        __builtins__=restricted_builtins,
        __name__=name,
        __package__=None,
        __doc__=None,
        verb_name=name
    )

    return env


_active_caller = contextvars.ContextVar("active_caller", default=None)
_active_player = contextvars.ContextVar("active_player", default=None)
_active_writer = contextvars.ContextVar("active_writer", default=None)
_active_parser = contextvars.ContextVar("active_parser", default=None)
_active_task_id = contextvars.ContextVar("active_task_id", default=None)
_verb_lookup_cache = contextvars.ContextVar("verb_lookup_cache", default=None)
_prop_lookup_cache = contextvars.ContextVar("prop_lookup_cache", default=None)
# A sentinel object (not a mutable default like []) so we can reliably detect whether
# a ContextManager is active: _active_caller_stack.get() is _UNSET means no session.
# Using a mutable list as the default would cause shared-state bugs — any code that
# appended to it outside a context would mutate the single default object permanently.
_UNSET = object()
_active_caller_stack = contextvars.ContextVar("active_caller_stack", default=_UNSET)
_perm_cache = contextvars.ContextVar("perm_cache", default=None)

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
        if name == "caller":
            return _active_caller.get()
        if name == "player":
            return _active_player.get()
        if name == "writer":
            return _active_writer.get()
        if name == "parser":
            return _active_parser.get()
        if name == "task_id":
            return _active_task_id.get()
        if name == "caller_stack":
            stack = _active_caller_stack.get()
            # Return a copy so callers cannot mutate the live stack.
            return [] if stack is _UNSET else list(stack)
        raise NotImplementedError(f"Unknown ContextManager variable: {name}")

    @classmethod
    def get_perm_cache(cls) -> dict | None:
        return _perm_cache.get()

    @classmethod
    def get_verb_lookup_cache(cls) -> dict | None:
        return _verb_lookup_cache.get()

    @classmethod
    def get_prop_lookup_cache(cls) -> dict | None:
        return _prop_lookup_cache.get()

    @classmethod
    def is_active(cls):
        # True only when __enter__ has been called and __exit__ has not yet run.
        # Verb.__call__ uses this to skip stack tracking for utility verb calls
        # that happen outside any user session (e.g. apply_default_permissions).
        return _active_caller_stack.get() is not _UNSET

    @classmethod
    def override_caller(cls, caller, this=None, verb_name=None, origin=None, player=None):
        attributes = {
            "this": this,
            "verb_name": verb_name,
            "caller": caller,
            "origin": origin,
            "player": player,
            "previous_caller": _active_caller.get(),
        }
        _active_caller.set(caller)
        caller_stack = _active_caller_stack.get()
        caller_stack.append(attributes)
        _active_caller_stack.set(caller_stack)

    @classmethod
    def pop_caller(cls):
        caller_stack = _active_caller_stack.get()
        if not caller_stack:
            raise RuntimeError("Caller stack is empty.")
        frame = caller_stack.pop()
        _active_caller_stack.set(caller_stack)
        _active_caller.set(frame["previous_caller"])

    def __init__(self, caller, writer, task_id=None, player=None):
        self.caller = caller
        self.caller_token = None
        self.player = player if player is not None else self.caller
        self.player_token = None
        self.writer = writer
        self.writer_token = None
        self.parser = None
        self.parser_token = None
        self.task_id = task_id
        self.task_id_token = None
        # A fresh list per instance so each session has its own isolated stack.
        self.active_caller_stack = []
        self.active_caller_stack_token = None
        # A fresh dict per instance for per-session permission caching.
        self.perm_cache = {}
        self.perm_cache_token = None
        # Per-session verb and property lookup caches keyed by (object_pk, name, ...).
        self.verb_lookup_cache = {}
        self.verb_lookup_cache_token = None
        self.prop_lookup_cache = {}
        self.prop_lookup_cache_token = None

    def set_parser(self, parser):
        self.parser = parser
        self.parser_token = _active_parser.set(self.parser)

    def __enter__(self):
        self.caller_token = _active_caller.set(self.caller)
        self.player_token = _active_player.set(self.player)
        self.writer_token = _active_writer.set(self.writer)
        self.task_id_token = _active_task_id.set(self.task_id)
        self.parser_token = _active_parser.set(self.parser)
        # Replacing _UNSET with a real list marks the session as active (is_active() → True)
        # and gives override_caller a mutable list to append to.
        self.active_caller_stack_token = _active_caller_stack.set(self.active_caller_stack)
        self.perm_cache_token = _perm_cache.set(self.perm_cache)
        self.verb_lookup_cache_token = _verb_lookup_cache.set(self.verb_lookup_cache)
        self.prop_lookup_cache_token = _prop_lookup_cache.set(self.prop_lookup_cache)
        return self

    def __exit__(self, cls, value, traceback):
        if self.caller_token:
            _active_caller.reset(self.caller_token)
        if self.player_token:
            _active_player.reset(self.player_token)
        if self.writer_token:
            _active_writer.reset(self.writer_token)
        if self.parser_token:
            _active_parser.reset(self.parser_token)
        if self.task_id_token:
            _active_task_id.reset(self.task_id_token)
        if self.active_caller_stack_token:
            # reset() restores to whatever the var held before __enter__'s set() call,
            # regardless of how many times override_caller/pop_caller mutated it since.
            _active_caller_stack.reset(self.active_caller_stack_token)
        if self.perm_cache_token:
            _perm_cache.reset(self.perm_cache_token)
        if self.verb_lookup_cache_token:
            _verb_lookup_cache.reset(self.verb_lookup_cache_token)
        if self.prop_lookup_cache_token:
            _prop_lookup_cache.reset(self.prop_lookup_cache_token)
