import contextvars
import warnings
import logging

from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.Guards import guarded_unpack_sequence

allowed_modules = (
    'termiverse.core',
    'hashlib',
    'string',
)

log = logging.getLogger(__name__)

user_context = contextvars.ContextVar("user")
def get_caller():
    return user_context.get(None)

output_context = contextvars.ContextVar("output")
def get_output():
    return output_context.get(None)

args_context = contextvars.ContextVar("args")
def get_args():
    return args_context.get(None)

class context(object):
    def __init__(self, caller, writer):
        from .models.object import AccessibleObject
        self.caller = AccessibleObject.objects.get(pk=caller.pk)
        self.writer = writer

    def __enter__(self):
        user_context.set(self.caller)
        output_context.set(self.writer)
        return self

    def __exit__(self, type, value, traceback):
        user_context.set(None)
        output_context.set(None)
        args_context.set(None)

def is_frame_access_allowed():
    return False

def massage_verb_code(code):
    """
    Take a given piece of verb code and wrap it in a function.

    This allows support of 'return' within verbs, and for verbs to return values.
    """
    code = code.replace('\r\n', '\n')
    code = code.replace('\n\r', '\n')
    code = code.replace('\r', '\n')
    code = '\n'.join(
        ['def verb():'] +
        ['\t' + x for x in code.split('\n') if x.strip()] +
        ['returnValue = verb()']
    )
    return code

def r_eval(caller, src, locals, globals, filename='<string>', runtype='eval'):
    src = massage_verb_code(src)
    return do_eval(caller, src, locals, globals, filename, runtype, 'eval')

def r_exec(caller, src, locals, globals, filename='<string>', runtype='exec'):
    src = massage_verb_code(src)
    return do_eval(caller, src, locals, globals, filename, runtype, 'exec')

def do_eval(caller, src, locals, globals, filename='<string>', runtype='exec', compileas='eval'):
    """
    Execute an expression in the provided environment.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=SyntaxWarning)
        code = compile_restricted(src, filename, compileas)

    value = eval(code, globals, locals)
    if("returnValue" in locals):
        return locals["returnValue"]
    return value

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

    for name in ['dict', 'dir', 'getattr', 'hasattr']:
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
