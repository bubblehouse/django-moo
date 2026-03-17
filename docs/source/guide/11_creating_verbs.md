# Creating MOO Programs with Python

> MOO stands for "MUD, Object Oriented." MUD, in turn, has been said to stand for many different things, but I tend to think of it as "Multi-User Dungeon" in the spirit of those ancient precursors to MUDs, Adventure and Zork.
>
> MOO, the programming language, is a relatively small and simple object-oriented language designed to be easy to learn for most non-programmers; most complex systems still require some significant programming ability to accomplish, however.
>
> Having given you enough context to allow you to understand exactly what MOO code is doing, I now explain what MOO code looks like and what it means. I begin with the syntax and semantics of expressions, those pieces of code that have values. After that, I cover statements, the next level of structure up from expressions. Next, I discuss the concept of a task, the kind of running process initiated by players entering commands, among other causes. Finally, I list all of the built-in functions available to MOO code and describe what they do.

## Verb Code Format

When creating verbs for storage in the database or in bootstrap verb files, the code must follow RestrictedPython's conventions and use Python as the execution language.

### Shebang Line (For Bootstrap Verbs)

Verb files that are part of the bootstrap system must begin with a "shebang" line that defines metadata:

```python
#!moo verb accept --on $room
```

The full syntax is:

```
#!moo verb verb_name1 [verb_name2] ...
    [--on object_name]
    [--dspec this|any|none|either]
    [--ispec PREP:SPEC [PREP:SPEC ...]]
```

**Parameters**:
- `verb_name`: The name(s) of the verb (space-separated for aliases like `#!moo verb put give`)
- `--on`: Object to attach the verb to. Supports the special `$property_name` syntax to refer to properties on the system object
- `--dspec`: Direct object specifier (defaults to `none`)
  - `this`: Requires a direct object from the player
  - `any`: Optional direct object
  - `none`: No direct object allowed
  - `either`: Can work with or without a direct object
- `--ispec`: Indirect object specifiers using prepositions
  - Format: `PREP:SPEC` where PREP is from the configured prepositions (e.g., `on`, `in`, `with`)
  - Example: `--ispec on:this in:this` allows "put X on Y" and "put X in Y"

**Examples**:

```python
#!moo verb accept --on $room
# A simple verb with no args, attached to the room object

#!moo verb drop --on $thing --dspec this
# A verb that requires a direct object

#!moo verb put give --on $thing --dspec this --ispec on:this --ispec in:this
# A verb with aliases, requiring direct and indirect objects
```

### RestrictedPython Execution

All verb code is compiled and executed within RestrictedPython's sandboxed environment. This means:

- Certain Python constructs are restricted for security reasons
- Only whitelisted modules and built-in functions are accessible
- Return statements can be used from anywhere (not just function end)
- Warnings about undefined variables can be ignored for injected variables like `this`, `passthrough`, `_`, `args`, and `kwargs`

**Whitelisted Modules**:
- `moo.sdk` - Public verb API (lookup, create, context, invoke, exceptions, etc.)
- `hashlib` - Hashing functions
- `re` - Regular expressions
- `datetime` - Date and time utilities
- `time` - Time utilities

**Whitelisted Built-ins**:
- `dict()` - Create dictionaries
- `enumerate()` - Enumerate iterables
- `getattr()` - Get attributes dynamically
- `hasattr()` - Check if attribute exists
- `list()` - Create lists
- `set()` - Create sets
- `sorted()` - Sort iterables

Attempting to import or use other modules will result in a security error.

## Python Implementation

As mentioned above, DjangoMOO uses Python as its in-game programming language. We usually need to start by importing one essential variable:

    from moo.sdk import context

The `context` object has a variety of attributes that are useful in verbs:

1. `player` – the Object that represents the user who called the verb
2. `caller` – the effective user that code is running with (usually the owner of the current executing verb)
3. `writer` - the Callable that prints text to the client connection
4. `task_id` - the current Celery task ID, if applicable
5. `parser` - the Parser object for the current task; inherited by synchronous sub-verb calls. Only `None` when a Celery task re-invokes a verb without an active player command (e.g., scheduled `invoke()` calls)
6. `task_time` - a `TaskTime(elapsed, time_limit, remaining)` namedtuple describing how much of the current task's time budget has been used. `remaining` and `time_limit` are `None` when no limit is configured. Useful for verbs that need to hand off long-running work before the budget runs out — see [Time-Aware Continuation](12_more_verbs.md#time-aware-continuation).

Also present in the global namespace is `verb_name`, the specific name used when the current verb was invoked.

### Verb Arguments

Since verb code is run in a function context, we always get a set of arguments that are available in verb code:

1. `this` - the Object where the current verb was found, often a child of the origin object
2. `passthrough()` - a function that calls the current function on the parent object, somewhat similar to super()
3. `_` - a reference to the #1 or "system" object
4. `args` - function arguments when run as a method, or an empty list
5. `kwargs` - function arguments when run as a method, or an empty dict

> **`this` is not the same as the caller.** Because the verb search uses "last match wins" (see [The Built-In Command Parser](07_parser.md)), `this` is set to the object on which the verb was *finally found* — typically the direct object when a `dspec` is set. Use `context.player` to identify who typed the command. Only use `this` when the verb is specifically designed to operate on the object it was dispatched on (e.g., a room's `accept` verb or an exit's `go` verb).

### Parser Method Reference

When a verb is invoked via the command parser, `context.parser` provides these methods to extract parsed arguments:

| Method | Returns | Notes |
|--------|---------|-------|
| `get_dobj()` | Direct object as an **Object** (DB lookup) | Raises `NoSuchObjectError` if string is not a real object |
| `get_dobj_str()` | Direct object as a **raw string** | Safe for plain text arguments (names, messages, etc.) |
| `has_dobj()` | `True` if dobj resolved to an Object | — |
| `has_dobj_str()` | `True` if dobj string is present | — |
| `get_pobj(prep)` | Indirect object as an **Object** for given prep | Raises `NoSuchObjectError`, `NoSuchPrepositionError` |
| `get_pobj_str(prep)` | Indirect object as a **raw string** for given prep | Raises `NoSuchPrepositionError` if prep not in command |
| `has_pobj(prep)` | `True` if iobj resolved to an Object | — |
| `has_pobj_str(prep)` | `True` if iobj string is present | — |

Use `get_dobj_str()` / `get_pobj_str()` when the argument is plain text (a message, a name to create, etc.). Use `get_dobj()` / `get_pobj()` only when you expect the argument to be a reference to an existing game object.

`NoSuchObjectError` and other exceptions from `moo.core.exceptions` all inherit from `UserError`. Any `UserError` raised inside a verb is automatically caught by the task runner and its message is shown to the player as a bold red line — no extra handling is needed. Letting `get_dobj()` raise `NoSuchObjectError` is the correct pattern when the argument must be a real object; the player will see `"There is no 'X' here."` automatically. Only catch these exceptions when you want to provide a different message or take alternative action.

### Error Handling

All exception classes in `moo.core.exceptions` inherit from `UserError`. Any `UserError` raised inside a verb — whether by the verb itself or by a called function like `get_dobj()` — is automatically caught by the task runner (`moo.core.tasks.parse_command`) and displayed to the player as a bold red message. Verbs do not need to wrap calls in `try/except` just to report errors to the player.

The common player-facing exceptions are all importable from `moo.sdk`:

| Exception | Default message |
|-----------|----------------|
| `NoSuchObjectError(name)` | `"There is no '<name>' here."` |
| `NoSuchVerbError(name)` | `"I don't know how to do that."` |
| `NoSuchPropertyError(name)` | `"There is no '<name>' property defined."` |
| `AmbiguousObjectError(name, matches)` | `"When you say '<name>', do you mean …?"` |
| `UsageError(message)` | The message string |

`UsageError` is the conventional way to signal bad syntax or missing arguments:

```python
from moo.sdk import UsageError

if not context.parser.has_dobj_str():
    raise UsageError(f"Usage: {verb_name} <target>")
```

Only catch a `UserError` subclass when you need a different message or fallback behaviour:

```python
from moo.sdk import NoSuchObjectError

try:
    target = context.parser.get_dobj()
except NoSuchObjectError:
    print("You'll need to be more specific.")
    return
```

Any uncaught exception that is not a `UserError` shows a generic `"An error occurred while executing the command."` to regular players and a full traceback to wizards.

### Sending Messages to Players

Two mechanisms exist for writing output to a player connection:

- **`obj.tell(msg)`** — Goes through `$player.tell`, which applies gag-list filtering and paranoia tracking before calling `write()`. Use this for normal in-game messages so that player preferences are respected.
- **`write(obj, msg)`** (imported from `moo.sdk`) — Only usable by Wizard-owned code. Low-level connection write; bypasses all filtering. Use sparingly, only when filtering must be skipped (e.g., system notifications).

In tests (where `CELERY_BROKER_URL = "memory://"`), both paths ultimately call `write()`, which emits `RuntimeWarning(f"ConnectionError({obj}): {msg}")` instead of sending to a real connection. Wrap test commands that trigger either path with `pytest.warns(RuntimeWarning)`:

```python
with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
    parse.interpret(ctx, "say Hello")
assert "Hello" in str(warnings.list[0].message)
```

### Getting and Setting the Values of Properties

The Django ORM brings in a few changes to how we access properties. We could potentially use the direct ORM method, like in this example:

```python
 qs = context.player.location.properties.filter(name="description")
 if qs:
     print(qs[0].value)
 else:
     print("No description.")
```

This doesn't honor inheritance, so you'll probably prefer to use `Object.get_property()`:

```python
 description = context.player.location.get_property('description')
 print(f"The description is: {description}")
```

It's possible to use the direct ORM method to *set* a property. This method can be useful if you want to further modify the property object or its permissions.

```python
 property = context.player.location.properties.create(name="description", value="A dark room.")
```

But similarly, you should probably just use:

```python
context.player.location.set_property("description", "A dark room.")
```

So far these examples haven't required any calls to `obj.save()`; this is only required for changes to the intrinsic object properties like `name`, `unique_name`, `obvious`, and `owner`.

> The LambdaCore database uses several properties on `#0`, the system object, for various special purposes. For example, the value of `#0.room` is the "generic room" object, `#0.exit` is the "generic exit" object, etc. This allows MOO programs to refer to these useful objects more easily (and more readably) than using their object numbers directly. To make this usage even easier and more readable, the expression
>
> `$name`
>
> (where name obeys the rules for variable names) is an abbreviation for
>
> `#0.name`
>
> Thus, for example, the value `$nothing` mentioned earlier is really `#-1`, the value of `#0.nothing`.

This syntax is supported in a few different places, but not in Python. To similate this feature, LambdaMOO Python code uses the magical `_` variable as a reference to the System Object, e.g., `_.root` instead of `$root`.
