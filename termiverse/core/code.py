import contextvars
import logging

from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.Guards import guarded_unpack_sequence

allowed_modules = (
    'hashlib',
    'string',
)

log = logging.getLogger(__name__)

user_context = contextvars.ContextVar("user")
def get_caller():
    return user_context.get(None)

def set_caller(obj):
    user_context.set(obj)

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

def r_eval(caller, src, environment={}, filename='<string>', runtype="eval"):
    """
    Evaluate an expression in the provided environment.
    """
    def _writer(s, is_error=False):
        if(s.strip()):
            # TODO: print should instead write to client
            log.error(s)#(caller, s, is_error=is_error)

    env = get_restricted_environment(_writer, environment.get('parser'))
    env['runtype'] = runtype
    env['caller'] = caller
    env.update(environment)

    code = compile_restricted(src, filename, 'eval')
    try:
        value =  eval(code, env)
    # except errors.UsageError as e:
    except Exception as e:
        if(caller):
            _writer(str(e), is_error=True)
        else:
            raise e

    return value

def r_exec(caller, src, environment={}, filename='<string>', runtype="exec"):
    """
    Execute an expression in the provided environment.
    """
    def _writer(s, is_error=False):
        if(s.strip()):
            # TODO: print should instead write to client
            log.error(s)#(caller, s, is_error=is_error)

    env = get_restricted_environment(_writer, environment.get('parser'))
    env['runtype'] = runtype
    env['caller'] = caller
    env.update(environment)

    code = compile_restricted(massage_verb_code(src), filename, 'exec')
    try:
        exec(code, env)
    # except errors.UsageError as e:
    except Exception as e:
        if(caller):
            _writer(str(e), is_error=True)
        else:
            raise e

    if("returnValue" in env):
        return env["returnValue"]

def get_restricted_environment(writer, p=None):
    """
    Given the provided parser object, construct an environment dictionary.
    """
    class _print_(object):
        def _call_print(self, s):
            writer(s)

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

    for name in ['dict', 'getattr', 'hasattr']:
        safe_builtins[name] = __builtins__[name]

    env = dict(
        _apply_           = lambda f,*a,**kw: f(*a, **kw),
        _print_           = lambda x: _print_(),
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
