# -*- coding: utf-8 -*-
"""
Development support resources for MOO programs
"""

import contextvars
import logging
import warnings

from django.conf import settings
from RestrictedPython import compile_restricted, compile_restricted_function
from RestrictedPython.Guards import (guarded_iter_unpack_sequence,
                                     guarded_unpack_sequence, safe_builtins)

log = logging.getLogger(__name__)


def interpret(source, name, *args, runtype="exec", **kwargs):
    from . import context

    globals = get_default_globals()  # pylint: disable=redefined-builtin
    globals.update(get_restricted_environment(name, context.writer))
    if runtype == "exec":
        return r_exec(source, {}, globals, *args, **kwargs)
    else:
        return r_eval(source, {}, globals, *args, **kwargs)


def compile_verb_code(body, filename):
    """
    Take a given piece of verb code and wrap it in a function.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=SyntaxWarning)
        result = compile_restricted_function(p="this=None, passthrough=None, _=None, *args, **kwargs", body=body, name="verb", filename=filename)
    return result


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
            Passthrough property access.
            """
            self.obj[key] = value  # pylint: disable=no-member

    def restricted_import(name, gdict, ldict, fromlist, level=-1):
        """
        Used to drastically limit the importable modules.
        """
        if name in settings.ALLOWED_MODULES:
            return __builtins__["__import__"](name, gdict, ldict, fromlist, level)
        raise ImportError("Restricted: %s" % name)

    def get_protected_attribute(obj, name, g=getattr):
        if name.startswith("_"):
            raise AttributeError(name)
        return g(obj, name)

    def set_protected_attribute(obj, name, value, s=setattr):
        if name.startswith("_"):
            raise AttributeError(name)
        return s(obj, name, value)

    def inplace_var_modification(operator, a, b):
        if operator == "+=":
            return a + b
        raise NotImplementedError("In-place modification with %s not supported." % operator)

    safe_builtins["__import__"] = restricted_import

    for n in settings.ALLOWED_BUILTINS:
        safe_builtins[n] = __builtins__[n]
    env = dict(
        _apply_=lambda f, *a, **kw: f(*a, **kw),
        _print_=lambda x: _print_(),
        _print=_print_(),
        _write_=_write_,
        _getattr_=get_protected_attribute,
        _getitem_=lambda obj, key: obj[key],
        _getiter_=iter,
        _inplacevar_=inplace_var_modification,
        _unpack_sequence_=guarded_unpack_sequence,
        _iter_unpack_sequence_=guarded_iter_unpack_sequence,
        __import__=restricted_import,
        __builtins__=safe_builtins,
        __metaclass__=type,
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
# A sentinel object (not a mutable default like []) so we can reliably detect whether
# a ContextManager is active: _active_caller_stack.get() is _UNSET means no session.
# Using a mutable list as the default would cause shared-state bugs — any code that
# appended to it outside a context would mutate the single default object permanently.
_UNSET = object()
_active_caller_stack = contextvars.ContextVar("active_caller_stack", default=_UNSET)

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
            # Return an empty list outside a session rather than exposing the sentinel.
            return [] if stack is _UNSET else stack
        raise NotImplementedError(f"Unknown ContextManager variable: {name}")

    @classmethod
    def is_active(cls):
        # True only when __enter__ has been called and __exit__ has not yet run.
        # Verb.__call__ uses this to skip stack tracking for utility verb calls
        # that happen outside any user session (e.g. apply_default_permissions).
        return _active_caller_stack.get() is not _UNSET

    @classmethod
    def override_caller(cls, caller, this=None, verb_name=None, origin=None, player=None, update_active=True):
        attributes = {
            "this": this,
            "verb_name": verb_name,
            "caller": caller,
            "origin": origin,
            "player": player,
        }
        if update_active:
            # Save the current caller so pop_caller can restore it precisely.
            # This is intentionally only done when update_active=True (e.g. set_task_perms),
            # NOT for normal Verb.__call__ pushes (update_active=False).
            #
            # Why: verbs like set_default_permissions call allow() internally, which
            # checks if the caller owns the subject. If we always set _active_caller to
            # verb.owner, a wizard-owned system verb running inside a user session would
            # suddenly become the caller — wizard wouldn't own the user's new object,
            # so the grant check would fail (chicken-and-egg: can't set permissions
            # because permissions aren't set yet). Keeping _active_caller as the session
            # caller (user) lets ownership checks pass correctly.
            attributes["previous_caller"] = _active_caller.get()
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
        if "previous_caller" in frame:
            # Only restore _active_caller if this frame actually changed it
            # (i.e. update_active=True was used when pushing). Frames pushed by
            # Verb.__call__ (update_active=False) have no previous_caller key,
            # so _active_caller is left untouched — the session caller stays stable.
            _active_caller.set(frame["previous_caller"])

    def __init__(self, caller, writer, task_id=None):
        self.caller = caller
        self.caller_token = None
        self.player = self.caller
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
