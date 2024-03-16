import contextvars
import warnings
import logging

from RestrictedPython import compile_restricted, compile_restricted_function
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.Guards import guarded_unpack_sequence

allowed_modules = (
    'termiverse.core',
    'hashlib',
    'string',
)

allowed_builtins = (
    'dict',
    'dir',
    'getattr',
    'hasattr'
)

log = logging.getLogger(__name__)

vars = contextvars.ContextVar("vars")
def get_context(name):
    d = vars.get({})
    return d.get(name)

class context(object):
    def __init__(self, caller, writer):
        from .models.object import AccessibleObject
        self.caller = AccessibleObject.objects.get(pk=caller.pk)
        self.writer = writer

    def __enter__(self):
        from . import api
        api.caller = self.caller
        api.writer = self.writer
        return self

    def __exit__(self, type, value, traceback):
        from . import api
        api.caller = None
        api.writer = None

def is_frame_access_allowed():
    return False

def compile_verb_code(body, filename):
    """
    Take a given piece of verb code and wrap it in a function.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=SyntaxWarning)
        result = compile_restricted_function(
            p = "",
            body = body,
            name = "verb",
            filename = filename
        )
    return result

def r_eval(src, locals, globals, filename='<string>'):
    code = compile_verb_code(src, filename)
    return do_eval(code, locals, globals, filename, runtype='eval')

def r_exec(src, locals, globals, filename='<string>'):
    code = compile_verb_code(src, filename)
    return do_eval(code, locals, globals, filename, runtype='exec')

def do_eval(code, locals, globals, filename='<string>', runtype='eval'):
    """
    Execute an expression in the provided environment.
    """
    if isinstance(code, str):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=SyntaxWarning)
            code = compile_restricted(code, filename, runtype)

        value = eval(code, globals, locals)
    else:
        exec(code.code, globals, locals)
        compiled_function = locals['verb']
        value = compiled_function(*[], **{})
    return value

def get_default_globals():
    return {
        "__name__": "__main__",
        "__package__": None,
        "__doc__": None
    }

def get_restricted_environment(writer):
    """
    Construct an environment dictionary.
    """
    class _print_(object):
        def _call_print(self,s):
            writer(str(s))

    class _write_(object):
        def __init__(self, obj):
            object.__setattr__(self, 'obj', obj)

        def __setattr__(self, name, value):
            """
            Private attribute protection using is_frame_access_allowed()
            """
            set_protected_attribute(self.obj, name, value)

        def __setitem__(self, key, value):
            """
            Passthrough property access.
            """
            self.obj[key] = value

    def restricted_import(name, gdict, ldict, fromlist, level=-1):
        """
        Used to drastically limit the importable modules.
        """
        if(name in allowed_modules):
            return __builtins__['__import__'](name, gdict, ldict, fromlist, level)
        raise ImportError('Restricted: %s' % name)

    def get_protected_attribute(obj, name, g=getattr):
        if(name.startswith('_') and not is_frame_access_allowed()):
            raise AttributeError(name)
        return g(obj, name)

    def set_protected_attribute(obj, name, value, s=setattr):
        if(name.startswith('_') and not is_frame_access_allowed()):
            raise AttributeError(name)
        return s(obj, name, value)

    def inplace_var_modification(operator, a, b):
        if(operator == '+='):
            return a+b
        raise NotImplementedError("In-place modification with %s not supported." % operator)

    safe_builtins['__import__'] = restricted_import

    for name in allowed_builtins:
        safe_builtins[name] = __builtins__[name]

    env = dict(
        _apply_           = lambda f,*a,**kw: f(*a, **kw),
        _print_           = lambda x: _print_(),
        _print            = _print_(),
        _write_           = _write_,
        _getattr_         = get_protected_attribute,
        _getitem_         = lambda obj, key: obj[key],
        _getiter_         = lambda obj: iter(obj),
        _inplacevar_      = inplace_var_modification,
        _unpack_sequence_ = guarded_unpack_sequence,
        __import__        = restricted_import,
        __builtins__      = safe_builtins,
    )

    return env
