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
- **test**: A minimal dataset used by core pytest tests in `moo/core/tests/`.

### Testing:
- `moo/core/tests` – The core pytest tests for basic functionality shared by all MOO universes
- `moo/bootstrap/default_verbs/tests/` — pytest integration tests for the verbs installed on the `default` dataset. These are the tests to write when adding or changing a `default_verbs/` verb.
- `moo/boostrap/test_verbs/` — These are **not** pytest tests; they are verb definitions loaded during `test.py` bootstrap initialisation.

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
  - `this`: Requires direct object to be where the verb was found
  - `any`: Accepts any string, but requires that something is specified
  - `none`: Will not match if a direct object is specified
  - `either`: Used for optional direct objects
- `--ispec`: Indirect object specifiers using prepositions
  - Format: `PREP:SPEC` where SPEC is `this`, `any`, or `none` and PREP is an item from `settings.PREPOSITIONS`

### Verb Dispatch and `this`

Understanding what `this` refers to is critical when writing verbs that take arguments.

**Search order** (`moo/core/parse.py`): For any command, the parser searches for a matching verb in this order:
1. The caller (player who typed the command)
2. Contents of the caller's inventory
3. The caller's location (room)
4. The direct object (`dobj`)
5. The indirect object (`pobj`)

**Last match wins.** The verb found *latest* in the search order is used, and `this` is set to the object it was found on.

**Consequence for `--dspec any` verbs on `$player`**: If both the caller *and* the dobj inherit the same verb (e.g., both are `$player` children), the dobj wins — `this` will be the dobj, not the caller.

```
@gag Player   →   this = Player (dobj), context.player = Wizard (caller)
page Player   →   this = Player (dobj), context.player = Wizard (caller)
```

**Use `context.player` for sender/initiator logic**, not `this`, whenever the verb is a player command that acts on behalf of the player who typed it. Use `this` only when the verb is specifically designed to be dispatched on another object (e.g., a room, container, or exit).

**Permission check antipattern**: Attempting to use the LambdaMOO idiom `if player != this: return "Permission denied."` will break whenever a dspec is set, because `this` will be the dobj rather than the caller. Use `context.player` directly to identify the initiator.

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

Verbs **must not**:
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
#!moo verb emote --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used for the pose type of interaction with other players. It functions in a similar way to the :say verb,
but instead places the player's name at the front of the text. The actual output is done in two stages. The :emote verb
is responsible for telling the player the action s/he has just performed. The emote1 verb is then called to tell the
other objects in the room of the pose action. This provides a two stage mechanism; either or both of the verbs can be
overridden to provide special effects.
"""

from moo.core import context

if context.parser.words:
    message = " ".join(context.parser.words[1:])
else:
    message = " ".join(args)

context.caller.tell("You " + message)
this.emote1(message)
```

### RestrictedPython Syntax Differences

Warnings and errors about undefined variables can be ignored for `this`, `passthrough`, `_`, `args`, and `kwargs`. These are injected by the execution environment.

Additionally, verbs can use the `return` keyword from anywhere, not just inside a function (courtesy of RestrictedPython compilation).

### Example: A Say Verb

```python
#!moo verb say --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context, write

if not args and not context.parser.has_dobj_str():  # pylint: disable=undefined-variable  # type: ignore
    print("What do you want to say?")
    return  # pylint: disable=return-outside-function  # type: ignore

if context.parser and context.parser.has_dobj_str():
    msg = context.parser.get_dobj_str()
else:
    msg = args[0]  # pylint: disable=undefined-variable  # type: ignore

for obj in context.caller.location.contents.all():
    write(obj, f"[bright_yellow]{context.caller.name}[/bright_yellow]: {msg}")
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

## Working with the MOO Context

Import and use the game context within verbs:

```python
#!moo verb create_item --on $player

"""Create a new object."""
from moo.core import context, create

if not args:
    print("Usage: create_item <name>")
    return

name = context.parser.get_dobj_str()
new_obj = create(name, location=this.location)

print(f"Created {new_obj.name}")
```

Common imports:
- `from moo.core import create, lookup` - Create/find objects
- `from moo.core.models import Object, Verb, Property` - Models
- `from moo.core import context` - Access the caller and other context

### Parser Method Reference

When a verb is invoked via the command parser, `context.parser` is a `moo.core.parse.Parser` instance. Use these methods to extract arguments:

| Method | Returns | Raises if missing |
|--------|---------|-------------------|
| `get_dobj()` | The direct object as an **Object** (DB lookup) | `Object.DoesNotExist` |
| `get_dobj_str()` | The direct object as a **raw string** | `Object.DoesNotExist` |
| `has_dobj()` | `True` if dobj resolved to an Object | — |
| `has_dobj_str()` | `True` if dobj string is present | — |
| `get_pobj(prep)` | Indirect object as an **Object** for given prep | `Object.DoesNotExist`, `NoSuchPrepositionError` |
| `get_pobj_str(prep)` | Indirect object as a **raw string** for given prep | `Object.DoesNotExist`, `NoSuchPrepositionError` |
| `has_pobj(prep)` | `True` if iobj resolved to an Object | — |
| `has_pobj_str(prep)` | `True` if iobj string is present | — |

**Key distinction**: `get_dobj()` / `get_pobj()` attempt a database lookup and raise `DoesNotExist` if the string doesn't match a real object. Use the `_str` variants when the argument is a plain string (a message, a name to create, etc.), not a reference to an existing game object.

**Note on naming**: The methods are `get_dobj_str` and `has_pobj_str` — there are no `…_string` variants.

## Testing Verbs

### Inline verbs (simple unit tests)

For quick tests of isolated logic, create a verb inline with `add_verb` and invoke it with `invoke_verb`:

```python
import pytest
from moo.core import code, create
from moo.core.models import Object

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_my_verb(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        obj = create("Test Object")
        obj.add_verb("my_verb", code='return "Hello"')
        result = obj.invoke_verb("my_verb")
        assert result == "Hello"
```

### Bootstrap integration tests (`default_verbs/tests/`)

Tests for verbs in `default_verbs/` live in `default_verbs/tests/` and run against the fully bootstrapped `default` world. Two fixtures from `moo/conftest.py` are required:

- **`t_init`**: Must be requested via `@pytest.mark.parametrize("t_init", ["default"], indirect=True)`. Bootstraps `default.py` and yields the system object (`#1`).
- **`t_wizard`**: Returns the Wizard player object, which starts in The Laboratory.

Capture output via a `_writer` callback; run player commands with `parse.interpret`; call `refresh_from_db()` before asserting database state:

```python
import pytest
from moo.core import code, create, lookup, parse
from moo.core.models import Object

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_drop_from_inventory(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        lab = t_wizard.location
        widget = create("widget", parents=[system.thing], location=t_wizard)

        parse.interpret(ctx, "drop widget")

        widget.refresh_from_db()
        assert widget.location == lab
```

Verbs can also be called directly as Python methods inside `code.ContextManager` — useful for testing helper/message verbs without going through the parser:

```python
with code.ContextManager(t_wizard, _writer):
    system = lookup(1)
    widget = create("widget", parents=[system.thing], location=t_wizard)

    # Equivalent to the MOO expression widget:drop_succeeded_msg()
    assert widget.drop_succeeded_msg() == f"You drop {widget}."
    assert widget.drop_failed_msg() == f"You can't seem to drop {widget} here."
```

To test that a lock prevents a `moveto`, set a `key` property on the destination. The expression `["!", id]` blocks the object whose id matches:

```python
destination.set_property("key", ["!", widget.id])
widget.moveto(destination)
widget.refresh_from_db()
assert widget.location != destination  # move was blocked by the lock
```

For commands that trigger connection-level notifications (movement between rooms, `say`, etc.), wrap the `parse.interpret` call with `pytest.warns`:

```python
with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
    parse.interpret(ctx, "go north")
assert [str(x.message) for x in warnings.list] == [
    f"ConnectionError(#{t_wizard.pk} (Wizard)): You leave ...",
]
```

### How bootstrap verbs are loaded

Verbs in `default_verbs/` are loaded by `bootstrap.load_verbs()` at the end of `default.py`:

1. The shebang line (`#!moo verb name --on $object`) is parsed for the verb name, target object, and argument specifiers.
2. The verb source is compiled via RestrictedPython on first invocation.
3. The verb is attached to the target object in the database.

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
from moo.core import context, invoke

invoke("Hello, finally.", verb=context.player.tell, delay=10, periodic=False)
return "Task started in background."
```

## Modifying Bootstrap Datasets

### Adding Objects to `default.py`

```python
from moo.core import create, lookup

# Create a new room
kitchen = create("Kitchen", parents=[rooms], location=None)
kitchen.set_property("description", "A cozy kitchen.")
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
- Use `if player != this:` as a permission guard — `this` is the *last matched object* in dispatch order (often the dobj), not the caller. This check will incorrectly fire on every normal invocation of a verb with `--dspec any`.
- Call `context.parser.get_dobj()` when you want a string message — it performs a DB lookup and raises `Object.DoesNotExist` if the string isn't a real object. Use `get_dobj_str()` for plain strings.
- Use `get_pobj_string()` / `has_pobj_string()` — these methods do not exist; the correct names are `get_pobj_str()` / `has_pobj_str()`.

### ✓ Do:
- Trust that `set_property()` and `add_verb()` automatically invalidate the attribute cache — no manual cache eviction is needed from verb code.
- Use `context.player` to identify who initiated a command (the sender/initiator)
- Use `this` only when the verb genuinely needs the object it was dispatched on (e.g., a room's `accept` or an exit's `go`)
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
