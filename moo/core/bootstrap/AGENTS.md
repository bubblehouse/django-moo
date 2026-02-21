# AGENTS.md: Bootstrap & Verb Code Development Guide

This document provides specific guidance for working with the DjangoMOO bootstrap system and verb code.

## Bootstrap System Overview

The bootstrap system initializes the game database with default game objects, classes, and verbs. It consists of:

### Files:
- `default.py`: Creates the `default` game world with rooms, players, and other game entities
- `test.py`: Creates the `test` dataset used by pytest
- `default_verbs/`: Directory of verb files that are installed on `default` game objects
- `test_verbs/`: Directory of verb files used for testing

### Datasets:
- **default**: The production game world. Used when running the server normally.
- **test**: A minimal dataset for testing. Used by all pytest tests.

## Verb Code Format

All verb files must start with a "shebang" line that defines metadata:

```python
#!moo verb name1 [name2] [name3] --on object_name [options]
```

### Shebang Syntax

```
#!moo verb verb_name1 [verb_name2] --on object_name
    [--dspec this|any|none|either]
    [--ispec PREP:SPEC [PREP:SPEC ...]]
```

**Parameters**:
- `verb_name`: The name(s) of the verb (space-separated for aliases)
- `--on`: Object ID to attach verb to. Supports the `$<name>` syntax to refer to properties on the system object
- `--dspec`: Direct object specifier
  - `this`: Requires a direct object
  - `any`: Optional direct object
  - `none`: No direct object
  - `either`: Can work either way (least common)
- `--ispec`: Indirect object specifiers using prepositions
  - Format: `PREP:SPEC` where SPEC is `this`, `any`, `none`, or `either` and PREP is an item from `settings.PREPOSITIONS`

### Examples

```python
#!moo verb accept --on $room
# A simple verb with no arguments
```

```python
#!moo verb drop --on $thing --dspec this
# A verb that requires a direct object
```

```python
#!moo verb put give --on $thing --dspec this --ispec on:this in:this
# A verb with multiple names, direct and indirect objects
```

## Verb Code Execution Environment

### Special Variables (Always Available)

These are automatically injected into every verb's execution context:

- **`this`**: The Object where the verb was found (often inherited from parent)
- **`passthrough`**: A function to invoke the verb on parent objects (like `super()` in OOP)
- **`_`**: Reference to the system object (usually ID #1)
- **`args`**: Tuple of positional arguments when called as a method
- **`kwargs`**: Dictionary of keyword arguments when called as a method
- **`verb_name`**: The specific name used to invoke this verb.
**Note**: Do not add these to function signatures in verb files; they are injected by RestrictedPython.

### Restricted Environment

Verb code runs in RestrictedPython's sandbox. All verbs are built with RestrictedPython's `compile_restricted_function` feature, and run inside a Python function definition that looks like this:

```python
def verb(this, passthrough, _, *args, **kwargs):
    """
    :param this: the Object where the current verb was found, often a child of the origin object
    :param passthrough: a function that calls the current function on the parent object, somewhat similar to super()
    :param _: a reference to the #1 or "system" object
    :param args: function arguments when run as a method, or an empty list
    :param kwargs: function arguments when run as a method, or an empty dict
    :return: Any
    """
```

Access is limited to (from settings):

**`ALLOWED_MODULES`**:
- `moo.core` - Core game API
- `hashlib` - Hashing functions
- `string` - String constants and utilities

**`ALLOWED_BUILTINS`**:
- `dir` - List attributes
- `getattr` - Get attributes
- `hasattr` - Check attributes
- `dict` - Dictionary creation
- `list` - List creation
- `set` - Set creation

### Important Restrictions

Verbs **cannot**:
- Import arbitrary modules (security restriction)
- Access filesystem directly
- Open network connections
- Modify Python internals
- Use `__import__` or `exec`/`eval`

Verbs **should not**:
- Perform long-running operations (use invoke() instead)
- Access database directly (use the ORM instead)
- Create threads or subprocesses (use invoke() instead)
- Modify global state (state changes should be on objects)

## Verb Code Patterns

### Basic Verb Structure

```python
#!moo verb my_verb --on $player

"""
Documentation for this verb.

this: The object this verb was found on
passthrough: Call to invoke on parent objects
_: System object reference
args: Function arguments (usually empty in interactive verbs)
kwargs: Keyword arguments (usually empty in interactive verbs)

Returns: Typically True/False or a string for output
"""
# Your verb code here
return True
```

### RestrictedPython Syntax Differences

Warnings and errors about undefined variables can be ignored for `this`, `passthrough`, `_`, `args`, and `kwargs`. These are injected by the execution environment.

Additionally, verbs can use the `return` keyword from anywhere, not just inside a function (courtesy of RestrictedPython compilation).

### Example: A Say Verb

```python
#!moo verb say --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

from moo.core import api, write

if not args and not api.parser.has_dobj_str():  # pylint: disable=undefined-variable  # type: ignore
    print("What do you want to say?")
    return  # pylint: disable=return-outside-function  # type: ignore

if api.parser and api.parser.has_dobj_str():
    msg = api.parser.get_dobj_str()
else:
    msg = args[0]  # pylint: disable=undefined-variable  # type: ignore

for obj in api.caller.location.contents.all():
    write(obj, f"[bright_yellow]{api.caller.name}[/bright_yellow]: {msg}")
```

### Early Return Pattern

One advantage of RestrictedPython is that `return` can be used anywhere:

```python
#!moo verb check_permission --on $player

"""Check if caller has permission."""
if not this.can_read():
    return "Permission denied."

# Multiple possible returns
if not args:
    return "Syntax: check_permission <object>"

return "Permission okay."
```

## Working with the Game API

Import and use the game API within verbs:

```python
#!moo verb create_item --on $player

"""Create a new object."""
from moo.core import api, create

if not args:
    print("Usage: create_item <name>")
    return

name = api.parser.get_dobj_str()
new_obj = create(name, location=this.location)

print(f"Created {new_obj.name}")
```

Common imports:
- `from moo.core import create, lookup` - Create/find objects
- `from moo.core.models import Object, Verb, Property` - Models
- `from moo.core import api` - Access the caller and other context

## Testing Verbs

### Unit Testing Verbs

Verbs are stored in the database and executed via `Object.invoke_verb()`:

```python
import pytest
from moo.core import create, code, lookup
from moo.core.models import Verb

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_my_verb(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    # Running with the current player and caller set to `t_wizard`
    with code.context(t_wizard, _writer) as ctx:
        # Create an object and add a verb
        obj = create("Test Object")
        obj.add_verb("my_verb", code='return "Hello"')
        # Invoke the verb
        result = obj.invoke_verb("my_verb")
        assert result == "Hello"
```

### Testing with Arguments

```python
@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_my_verb(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    # Running with the current player and caller set to `t_wizard`
    with code.context(t_wizard, _writer) as ctx:
      obj = create("Test")
      obj.add_verb("greet", code='''
name = args[0] if args else "Friend"
return f"Hello, {name}!"
''')
      result = obj.invoke_verb("greet", args=["Alice"])
      assert result == "Hello, Alice!"
```

### Bootstrap Verbs

Verbs in `default_verbs/` or `test_verbs/` are loadedd during `moo_init`:

1. The shebang line is parsed
2. The filename is read and processed
3. The verb is attached to the appropriate object

Verb code is compiled via RestrictedPython the first time it's invoked.

## Best Practices for Verb Development

### 1. Check Permissions Early
```python
if not this.can_caller("write"):
    return "Permission denied."
```

### 2. Validate Arguments
```python
if not args:
    return "Usage: verb_name <required_arg>"
```

### 3. Use Descriptive Returns
- Return `True/False` for success/failure
- Return strings for player-facing messages

### 5. Handle Errors Gracefully
```python
try:
    # Verb code
except AttributeError:
    return "Invalid object reference."
except ValueError:
    return "Invalid argument value."
```

### 7. Avoid Long Operations
If a verb needs to do something time-consuming:

```python
from moo.core import api, invoke

invoke("Hello, finally.", verb=api.player.tell, delay=10, periodic=False)
return "Task started in background."
```

## Modifying Bootstrap Datasets

### Adding Objects to `default.py`

```python
from moo.core import create, lookup

# Create a new room
kitchen = create("Kitchen", parents=[rooms], location=None)
kitchen.set_property("description", "A cozy kitchen.", inherit_owner=True)
```

### Adding Verbs to Bootstrap Datasets

Do: Create verb file in `default_verbs/` or `test_verbs/`

Do Not: Add verb directly in bootstrap code:
```python
obj = lookup("some object")
obj.add_verb("my_verb", code='return "verb result"')
```

## Common Mistakes

### ❌ Don't:
- Assume variables are defined (they might be inherited differently)
- Perform blocking I/O operations
- Access the filesystem
- Hardcode object IDs (use `lookup("name")` or properties instead)
- Create objects in loops without considering performance
- Modify `args` or `kwargs` directly (they're read-only)

### ✓ Do:
- Use `lookup()` or properties to find objects
- Return meaningful error messages to players
- Use permission checks (`can_caller()`)
- Test verbs with multiple argument combinations
- Document complex verb logic with comments
- Use type hints in Python code (not in verbs, they're restricted)

## Debugging Verbs

### In Django Shell
```python
from moo.core import lookup

obj = lookup("some object")
result = obj.my_verb()
print(result)
```

### With Try/Except Blocks
```python
#!moo verb debug_verb --on $player

try:
    # Verb code
    risky_operation()
except Exception as e:
    return f"Error: {str(e)}"
```

## Additional Resources

- See `default_verbs/` and `test_verbs/` for example verbs in this repository
- RestrictedPython documentation: https://restrictedpython.readthedocs.io/
- Django ORM documentation: https://docs.djangoproject.com/en/stable/topics/db/models/
