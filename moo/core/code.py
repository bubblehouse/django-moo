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
    from . import api

    globals = get_default_globals()  # pylint: disable=redefined-builtin
    globals.update(get_restricted_environment(name, api.writer))
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


_active_user = contextvars.ContextVar("active_user", default=None)
_active_writer = contextvars.ContextVar("active_writer", default=None)
_active_parser = contextvars.ContextVar("active_parser", default=None)

class context:
    """
    The context class is what holds critical per-execution information such as
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
            return _active_user.get()
        if name == "writer":
            return _active_writer.get()
        if name == "parser":
            return _active_parser.get()
        raise NotImplementedError(f"Unknown context variable: {name}")

    def __init__(self, caller, writer):
        from .models.object import AccessibleObject

        self.caller = AccessibleObject.objects.get(pk=caller.pk) if caller else None
        self.caller_token = None
        self.writer = writer
        self.writer_token = None
        self.parser = None
        self.parser_token = None

    def set_parser(self, parser):
        self.parser = parser
        self.parser_token = _active_parser.set(self.parser)

    def __enter__(self):
        self.caller_token = _active_user.set(self.caller)
        self.writer_token = _active_writer.set(self.writer)
        return self

    def __exit__(self, cls, value, traceback):
        if self.caller_token:
            _active_user.reset(self.caller_token)
        if self.writer_token:
            _active_writer.reset(self.writer_token)
        if self.parser_token:
            _active_parser.reset(self.parser_token)
