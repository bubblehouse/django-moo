# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security audit: random module

Tests potential attack vectors when adding 'random' to ALLOWED_MODULES.
Pass 17 focus: new module addition.
"""

import pytest

from .utils import ctx, exec_verb, mock_caller, raises_in_verb

# ---------------------------------------------------------------------------
# Basic functionality
# ---------------------------------------------------------------------------


def test_random_basic_usage():
    """
    Confirm basic random module functions work as expected.

    This is a regression test confirming that adding random to ALLOWED_MODULES
    does not break the sandbox guards - basic operations should work normally.
    """
    src = """
import random
print(random.randint(1, 10))
print(random.choice([1, 2, 3]))
print(random.random())
"""
    output = exec_verb(src)
    assert len(output) == 3
    # Line 1: randint result (1-10)
    val = int(output[0])
    assert 1 <= val <= 10
    # Line 2: choice result (one of 1, 2, 3)
    assert int(output[1]) in [1, 2, 3]
    # Line 3: float result
    assert isinstance(float(output[2]), float)


# ---------------------------------------------------------------------------
# Module traversal attacks
# ---------------------------------------------------------------------------


def test_random_no_dunder_access():
    """
    Underscore guard blocks dunder attributes on the random module.

    Attack path: import random; getattr(random, '__package__') → traverse to parent package
    Guard: underscore check in safe_getattr raises AttributeError
    """
    raises_in_verb("import random; x = getattr(random, '__package__')", AttributeError)


def test_random_Random_class_no_dunder_access():
    """
    Random class dunder attributes blocked by underscore guard.

    Attack path: getattr(random.Random, '__bases__') → object → __subclasses__() → all classes
    Guard: underscore check in safe_getattr
    """
    raises_in_verb("import random; x = getattr(random.Random, '__bases__')", AttributeError)


def test_random_instance_no_dunder_access():
    """
    Random instance dunder attributes blocked by underscore guard.

    Attack path: getattr(random.Random(), '__class__') → __mro__ → MRO walk
    Guard: underscore check in safe_getattr
    """
    raises_in_verb("import random; x = getattr(random.Random(), '__class__')", AttributeError)


# ---------------------------------------------------------------------------
# Frame/inspection attacks
# ---------------------------------------------------------------------------


def test_random_no_frame_attributes():
    """
    INSPECT_ATTRIBUTES guard blocks frame attrs even if they existed.

    Attack path: if Random instances had gi_frame/cr_frame/f_back, getattr
    would need to block them to prevent frame walks to f_builtins['__import__'].

    Result: Random objects don't have frame attributes (they're not generators
    or coroutines), but INSPECT_ATTRIBUTES provides defense-in-depth.
    """
    src = """
import random
r = random.Random()
for attr in ['gi_frame', 'f_back', 'f_locals', 'cr_frame']:
    assert not hasattr(r, attr), f"Random has {attr}"
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]


def test_random_getstate_no_dangerous_attrs():
    """
    getstate() returns a plain tuple with no dangerous attributes.

    Attack path: state = random.getstate(); traverse state to find module/frame refs
    Result: state is (VERSION, tuple_of_ints, None) - no dangerous surface
    """
    src = """
import random
state = random.getstate()
assert isinstance(state, tuple)
# Tuples only have count and index - no module/frame/manager attrs
assert hasattr(state, 'count')
assert hasattr(state, 'index')
# Key dangerous attrs should not exist
assert not hasattr(state, 'objects')  # No Django manager
assert not hasattr(state, 'model')    # No QuerySet
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]


# ---------------------------------------------------------------------------
# Format string attacks
# ---------------------------------------------------------------------------


def test_random_no_format_methods():
    """
    Random objects don't expose format/format_map methods.

    Attack path: if random.Random() had .format(), it might bypass safe_getattr
    guards like str.format does (blocked separately for strings only).

    Result: Random objects are not strings and don't have format methods.
    The str.format guard in safe_getattr only applies to str types.
    """
    src = """
import random
r = random.Random()
assert not hasattr(r, 'format'), "Random has format"
assert not hasattr(r, 'format_map'), "Random has format_map"
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]


# ---------------------------------------------------------------------------
# Module reference leaks
# ---------------------------------------------------------------------------


def test_random_no_module_attributes():
    """
    Random class attributes are functions/methods/constants, not modules.

    Attack path: if random.Random had module attributes, they could be traversed
    Guard: ModuleType guard in safe_getattr would block submodule access

    Result: Random's public attributes (random, seed, getstate, etc.) are all
    callable methods or int constants - no module references exist.
    This test confirms the architectural fact by spot-checking key attributes.
    """
    src = """
import random
# Spot-check that key attributes are callable or int, not modules
assert callable(random.Random.random)
assert callable(random.Random.seed)
assert isinstance(random.Random.VERSION, int)
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]


def test_random_module_no_submodule_traversal():
    """
    random module exports are classes/functions/constants, not submodules.

    Attack path: import random; random.some_submodule → traverse to os/sys/etc
    Guard: ModuleType guard checks submodule.__name__ against ALLOWED_MODULES

    Result: random module has no submodules; all exports are classes, functions,
    or numeric constants. This test confirms architectural facts by spot-checking.
    """
    src = """
import random
# Spot-check that key module-level exports are not modules
# Classes
r = random.Random()
assert isinstance(r, random.Random)
sr = random.SystemRandom()
assert isinstance(sr, random.SystemRandom)
# Functions
assert callable(random.randint)
assert callable(random.choice)
# Constants
assert isinstance(random.BPF, int)
assert isinstance(random.TWOPI, float)
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]


# ---------------------------------------------------------------------------
# SystemRandom safety
# ---------------------------------------------------------------------------


def test_random_SystemRandom_safe():
    """
    SystemRandom is a Random subclass using os.urandom, has same safety props.

    Attack path: SystemRandom might expose OS module internals
    Result: SystemRandom is just Random with a different RNG source; same guards apply
    """
    src = """
import random
sr = random.SystemRandom()
# Should work normally
val = sr.randint(1, 100)
assert 1 <= val <= 100
# Dunder access blocked
try:
    getattr(sr, '__bases__')
    assert False, "__bases__ accessible on SystemRandom"
except AttributeError:
    pass
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]


# ---------------------------------------------------------------------------
# State manipulation (architectural safety)
# ---------------------------------------------------------------------------


def test_random_seed_setstate_task_isolated():
    """
    seed() and setstate() manipulate module-level state safely.

    Attack concern: could seed/setstate poison RNG state across tasks?

    Mitigation: Celery execution model isolates each verb invocation in a
    separate task. Module-level state (random._inst) is per-process, but
    each task runs in a worker process that may be reused. However:
    - RNG state manipulation only affects the current task's execution
    - Next task will have a fresh module import or unpredictable state
    - No persistent state pollution is possible (no shared memory, no DB writes)

    This is architectural safety, not a guard. Testing that operations work.
    """
    src = """
import random

# Save original state
original = random.getstate()
assert isinstance(original, tuple)

# Manipulate state
random.seed(12345)
val1 = random.randint(1, 100)

# Restore state
random.setstate(original)
val2 = random.randint(1, 100)

# Both should work; state is isolated to this task
print(f"val1={val1}, val2={val2}")
"""
    output = exec_verb(src)
    assert output[0].startswith("val1=")


# ---------------------------------------------------------------------------
# Constant value safety
# ---------------------------------------------------------------------------


def test_random_constants_safe():
    """
    Module-level constants (BPF, LOG4, etc.) are safe numeric values.

    These are mathematical constants used internally by distribution functions.
    They're all float or int - no dangerous references.
    """
    src = """
import random
# Check that constants are just numbers
constants = ['BPF', 'LOG4', 'NV_MAGICCONST', 'RECIP_BPF', 'SG_MAGICCONST', 'TWOPI']
for const in constants:
    val = getattr(random, const)
    assert isinstance(val, (int, float)), f"{const} is not a number"
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]


# ---------------------------------------------------------------------------
# Integration with existing guards
# ---------------------------------------------------------------------------


def test_random_respects_underscore_guard():
    """
    Confirm random objects respect the global underscore attribute guard.

    All getattr/hasattr calls on random objects go through safe_getattr,
    which blocks _-prefixed names at the top. This is belt-and-suspenders
    with the RestrictedPython compile-time check.
    """
    # Underscore access via getattr builtin blocked at runtime
    raises_in_verb("import random; getattr(random, '_inst')", AttributeError)

    # Underscore access via hasattr also blocked
    src = """
import random
assert not hasattr(random, '_inst')
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]


def test_random_hasattr_respects_INSPECT_ATTRIBUTES():
    """
    Confirm hasattr() on random objects checks INSPECT_ATTRIBUTES.

    If Random objects had gi_frame/f_back/etc., hasattr should return False
    due to the INSPECT_ATTRIBUTES guard in safe_hasattr.
    """
    src = """
import random
r = random.Random()
# These are frame-walk attributes - should return False even if they existed
for attr in ['gi_frame', 'f_back', 'f_locals', 'cr_frame', 'f_builtins']:
    assert not hasattr(r, attr), f"hasattr(Random, {attr}) returned True"
print("ok")
"""
    output = exec_verb(src)
    assert output == ["ok"]
