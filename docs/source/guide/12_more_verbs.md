# More Verb Patterns

## Calling Other Verbs

Like properties, the default Django ORM doesn't honor inheritance, so there's a few custom methods on Object instances to help out.

The simplest way to invoke another verb (as a method) from a running verb is with:

```python
obj.invoke_verb("announce", *args, **kwargs)
```

or using the getattr override:

```python
obj.announce(*args, **kwargs)
```

This works for many convenience functions, but whatever time these functions use will count against the default
verb timeout of 3 seconds.

If you're limited to 3 seconds in a Verb, how do you create longer tasks? The key is to compose your function
into multiple Verb calls, which you can invoke asynchronously using the `invoke()` function:

```{eval-rst}
.. py:currentmodule:: moo.core
.. autofunction:: invoke
   :no-index:
```

Using `invoke()` let's create a bad example of a talking parrot:

```python
from moo.sdk import context, invoke
if context.parser is not None:
    invoke(context.parser.verb, delay=30, periodic=True)
    return
for obj in context.caller.location.filter(player__isnull=False):
    context.writer(obj, "A parrot squawks.")
```

Right now it's just repeating every thirty seconds, but we can make it slightly more intelligent
by handling our own repeating Verbs:

```python
from moo.sdk import context, invoke
if context.parser is not None:
    invoke(context.parser.verb, delay=30, value=0)
    return
value = kwargs['value'] + 1
for obj in context.caller.location.filter(player__isnull=False):
    context.writer(obj, f"A parrot squawks {value}.")
invoke(context.parser.verb, delay=30, value=value)
```

Let's say we didn't want to handle writing ourselves (we shouldn't) and wanted instead
to re-use the `say` Verb.

```python
from moo.sdk import context, invoke
if context.parser is not None:
    say = context.caller.get_verb('say', recurse=True)
    invoke(verb=context.parser.verb, callback=say, delay=30, value=0)
    return
value = kwargs['value'] + 1
return f"A parrot squawks {value}."  # return value passed to the 'say' callback
```

## Time-Aware Continuation

`invoke()` gives each verb its own 3-second budget, but what if a single verb needs to do work that could take arbitrarily long — like iterating over hundreds of objects? The answer is to check how much time remains and hand the unfinished work off to a fresh task before the budget runs out.

`context.task_time` returns a `TaskTime` namedtuple (or `None` if no time limit is configured):

```python
from moo.sdk import context

tt = context.task_time
# tt.elapsed   — seconds since this task started
# tt.time_limit — the configured hard limit (e.g. 3.0), or None
# tt.remaining  — seconds left before the task is killed, or None
```

The canonical pattern is to check `remaining` before each unit of work in a loop. When it drops below a safety threshold, collect whatever is left, schedule it as a new task via `invoke()`, and return:

```python
from moo.sdk import context, invoke

TIME_THRESHOLD = 0.5  # hand off when 0.5 s remain

def process_batch(items):
    count = 0
    for i, item in enumerate(items):
        tt = context.task_time
        if tt and tt.remaining is not None and tt.remaining <= TIME_THRESHOLD:
            remaining = items[i:]
            reload_verb = context.parser.verb if context.parser else this.get_verb("process")
            invoke(remaining, verb=reload_verb)
            context.player.tell(f"  Continuing in a new task ({len(remaining)} item(s) remaining)...")
            return True, count
        context.player.tell(f"  Processing {item}...")
        do_work(item)
        count += 1
    return False, count
```

A few things to note:

- `context.task_time` may return `None` in test environments where no task time limit is configured. Always guard with `if tt and tt.remaining is not None`.
- Use `context.player.tell()` (not `print()`) for progress messages inside the loop. `tell()` routes through `write()` and is delivered immediately; `print()` buffers until the verb returns.
- Materialize the queryset to a `list()` before the loop so the DB cursor doesn't stay open across the time check.
- Get the verb reference for `invoke()` from `context.parser.verb` (no DB hit when called from the parser), falling back to `this.get_verb(name)` in continuation mode where `context.parser` is `None`.
- Keep the continuation args minimal — just the list of remaining work items. There's no need to pass accumulated counts or error lists since progress messages were already delivered via `tell()`.

When the continuation task fires, add a branch at the top of the verb to detect that it was invoked with pre-computed work rather than through the parser:

```python
if args and isinstance(args[0], list):
    # Continuation mode: args[0] is a list of remaining items
    continued, count = process_batch(list(args[0]))
    if not continued:
        context.player.tell(f"Done. Processed {count} item(s).")
else:
    # Normal parser path
    items = list(get_all_items())
    continued, count = process_batch(items)
    if not continued:
        context.player.tell(f"Done. Processed {count} item(s).")
```

The `@reload` verb in `moo/bootstrap/default_verbs/programmer/at_reload.py` is the reference implementation of this pattern.

## Returning a Value from a Verb

> The MOO program in a verb is just a sequence of statements. Normally, when the verb is called, those statements are simply executed in order and then the integer 0 is returned as the value of the verb-call expression. Using the `return` statement, one can change this behavior.

`return` can be used from anywhere in verb code, not just at the end of a function — this is one of the advantages of how RestrictedPython compiles verbs.

**Important:** `return "some string"` does **not** display anything to a player when the verb is invoked as a command. The return value goes back to whatever called the verb, which is discarded for top-level player commands. To display output, use `print()`. Use a bare `return` to exit early:

```python
# CORRECT: print the message, then return
if not args:
    print(f"Usage: {verb_name} <object_name>")
    return

# WRONG: the player sees nothing
if not args:
    return "Usage: check_object <object_name>"
```

Returning a value is useful when a verb is designed to be called by other verbs (as a helper method), not by players directly. For example, `$thing.take_succeeded_msg()` returns a formatted string that `take.py` then passes to `print()`.

```python
#!moo verb check_object --on $room

from moo.sdk import context, NoSuchPropertyError

# Early exit for missing arguments
if not args:
    print(f"Usage: {verb_name} <object_name>")
    return

# Find the object
obj_name = args[0]
found_objs = this.contents.filter(name=obj_name)

if not found_objs.exists():
    print(f"I don't see '{obj_name}' here.")
    return

# Check permissions
obj = found_objs.first()
if not obj.can_caller("read"):
    print("You don't have permission to examine that.")
    return

# Display result
try:
    desc = obj.get_property("description")
except NoSuchPropertyError:
    desc = "(no description)"

print(f"Object: {obj.name}")
print(f"Description: {desc}")
```

## Handling Verb Errors

DjangoMOO defines a number of custom exceptions, but there's still a lot of inconsistency where they're used. At this
time raising any of them from verb code will rollback the transaction as if the verb never executed.

```{eval-rst}
.. py:currentmodule:: moo.core.exceptions
.. autoclass:: UsageError
   :no-index:
.. autoclass:: UserError
   :no-index:
.. autoclass:: AccessError
   :no-index:
.. autoclass:: AmbiguousObjectError
   :no-index:
.. autoclass:: AmbiguousVerbError
   :no-index:
.. autoclass:: ExecutionError
   :no-index:
.. autoclass:: NoSuchPrepositionError
   :no-index:
.. autoclass:: QuotaError
   :no-index:
.. autoclass:: RecursiveError
   :no-index:
```

## Additional SDK Functions

Beyond `lookup()`, `create()`, `write()`, and `invoke()`, `moo.sdk` provides several more functions for wizard-owned verbs.

### `open_editor(obj, initial_content, callback_verb, *args, content_type="text")`

Opens a full-screen text editor in the player's SSH terminal. When the player saves and closes the editor, `callback_verb` is called with the saved text as its first argument, followed by any additional `*args`.

```python
from moo.sdk import context, open_editor

# Open the editor pre-filled with existing text; call obj.save_verb when done
open_editor(context.player, existing_text, obj.save_verb, content_type="python")
```

`content_type` controls syntax highlighting: `"text"` (default), `"python"`, or `"json"`.

### `open_paginator(obj, content, content_type="text")`

Opens a full-screen read-only paginator for long text (help pages, listings, etc.).

```python
from moo.sdk import context, open_paginator

open_paginator(context.player, long_help_text, content_type="text")
```

### `players()`

Returns all player avatar Objects (connected or not).

```python
from moo.sdk import players

for p in players():
    print(p.title())
```

### `connected_players(within=None)`

Returns player Objects that have been active within the given time window (default: 5 minutes).

```python
from moo.sdk import connected_players
from datetime import timedelta

active = connected_players(within=timedelta(minutes=10))
print(f"{len(active)} player(s) online.")
```

### `set_task_perms(who)`

Context manager. Temporarily runs the enclosed code with the permissions of `who`. Useful when a wizard-owned verb needs to perform an action as a different user or as the system object.

```python
from moo.sdk import set_task_perms, lookup

system = lookup(1)
with set_task_perms(system):
    obj.set_property("owner", system)  # runs as if owned by the system object
```

All four functions above are only callable from wizard-owned verbs.

## Best Practices for Verb Development

### 1. Always Check Permissions First

```python
from moo.sdk import context

if not this.can_caller("write"):
    print("Permission denied.")
    return
```

### 2. Validate Arguments Early

```python
from moo.sdk import UsageError

if len(args) < 2:
    raise UsageError(f"Usage: {verb_name} <arg1> <arg2>")
```

Or with `print()` if you prefer a softer exit:

```python
if len(args) < 2:
    print(f"Usage: {verb_name} <arg1> <arg2>")
    return
```

### 3. Use the MOO Context

```python
from moo.sdk import context

# context.caller is the effective caller (usually verb owner)
# context.player is the player executing the command
# context.writer sends output to the player
# context.parser contains parsed command info
```

### 4. Use `print()` for Player-Visible Output

`return "message"` does not show anything to the player in a command verb. Use `print()` for feedback:

```python
# CORRECT: player sees this
if not obj:
    print("That object doesn't exist.")
    return

print("Object created successfully.")

# WRONG: return value is silently discarded
return "Object created successfully."
```

`return` a value only when you are writing a helper verb designed to be called by other verb code, not by players directly.

### 5. Avoid Subscript Augmented Assignment

RestrictedPython silently fails to compile verbs that use `+=` on a dictionary subscript. The failure produces a `TypeError: exec() arg 1 must be a string, bytes or code object` at runtime, not a clear syntax error.

```python
# BLOCKED — causes a silent compilation failure
results["passed"] += 1

# CORRECT — use a plain variable instead
passed += 1
failed += 1
```

If a verb inexplicably does nothing or crashes with a `TypeError` about `exec()`, check for this pattern.

### 6. Respect the Verb Time Limit

Each verb execution (including synchronous calls to other verbs) should complete in less than 3 seconds, or Celery will terminate the task. For verbs that loop over many items, use the time-aware continuation pattern described in [Time-Aware Continuation](#time-aware-continuation) above.
