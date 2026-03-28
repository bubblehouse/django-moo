# moo.sdk Reference

All public verb API is in `moo.sdk`. Only `moo.sdk`, `hashlib`, and `string` may be imported in verb code.

```python
from moo.sdk import context, lookup, create, invoke, write
from moo.sdk import NoSuchObjectError, NoSuchVerbError, NoSuchPropertyError, AmbiguousObjectError
```

## `context`

A read-only object exposing the current execution context. All attributes are read-only — attempting to set them raises `AttributeError`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `context.caller` | Object | The object whose permissions are in effect (the verb's owner) |
| `context.player` | Object | The player who initiated the command session; use this for the "who typed this" identity |
| `context.parser` | Parser or None | Parser instance for the current task; inherited by synchronous sub-verb calls. `None` only when a Celery task re-invokes a verb outside any player command (e.g., scheduled `invoke()` calls) |
| `context.writer` | callable | Low-level write function for the current player's console |
| `context.task_id` | str | Celery task ID of the current execution |
| `context.task_time` | TaskTime or None | Timing info for the current task: `elapsed`, `time_limit`, `remaining` (all in seconds). `None` when no time limit is configured (e.g. in tests). |
| `context.caller_stack` | list | Stack of callers (for nested verb invocations) |

`context.player` is the right variable to use when you need to know who typed the command. `context.caller` reflects the verb's permission context and may differ when `set_task_perms` is used.

## `lookup(x)`

Find a game object globally.

```python
lookup(x: int | str) -> Object
```

- `lookup(1)` — returns the system object
- `lookup("Wizard")` — finds by name or alias (case-insensitive)
- `lookup("$thing")` — returns the value of property `thing` on the system object

Raises `NoSuchObjectError` if nothing matches. Never returns `None`.

## `create(name, *, parents=None, location=None, owner=None)`

Create and return a new Object.

```python
create("Widget", parents=[system.thing], location=t_wizard)
```

- `parents` defaults to `[system.root_class]` if omitted
- `location` defaults to the caller's location if omitted
- `owner` defaults to `context.caller` if omitted
- Calls the new object's `initialize` verb if one exists
- Decrements `ownership_quota` on the owner if it exists
- Raises `QuotaError` if the owner's quota is exhausted
- Raises `PermissionError` if the caller cannot `derive` from the parent

## `write(obj, message)`

Send a message directly to a player's console, bypassing the tell verb chain and all filtering.

```python
write(obj, "You have been teleported.")
```

- Only callable from wizard-owned verbs. Raises `UserError` otherwise.
- In tests (`CELERY_BROKER_URL = "memory://"`), emits `RuntimeWarning` instead of writing. Capture with `pytest.warns(RuntimeWarning)`.

For most cases, prefer `obj.tell(msg)` which goes through gag lists and paranoia filtering.

## `invoke(verb, *args, callback=None, delay=0, periodic=False, cron=None, **kwargs)`

Asynchronously execute a Verb in a separate Celery task with its own timeout.

```python
invoke("Task started.", verb=context.player.tell, delay=10)
invoke(verb=obj.some_verb, args=(arg1, arg2))
```

- `verb` — a Verb reference obtained via `obj.verb_name` attribute access
- `delay` — seconds to wait before executing (cannot combine with `cron`)
- `periodic=True` — repeat on the `delay` interval (wizard-owned verbs only)
- `cron` — crontab expression, e.g., `"0 * * * *"` (wizard-owned verbs only)
- `callback` — optional Verb to receive the result
- Returns a `PeriodicTask` instance for periodic/cron tasks, `None` for one-shots

Use `invoke` when a sub-verb would exceed the 3-second verb time limit, or when you want a delayed or recurring action.

### Time-aware continuation pattern

For verbs that loop over many items, check `context.task_time.remaining` before each iteration and hand off remaining work when time is nearly exhausted:

```python
TIME_THRESHOLD = 0.5  # seconds

def process_batch(items):
    count = 0
    for i, item in enumerate(items):
        tt = context.task_time
        if tt and tt.remaining is not None and tt.remaining <= TIME_THRESHOLD:
            remaining_pks = [x.pk for x in items[i:]]
            verb = context.parser.verb if context.parser else this.get_verb("myverb")
            invoke(remaining_pks, verb=verb)
            context.player.tell(f"  Continuing ({len(remaining_pks)} remaining)...")
            return True, count
        context.player.tell(f"  Processing {item}...")
        item.do_work()
        count += 1
    return False, count

# Top of the verb — detect continuation mode
if args and isinstance(args[0], list):
    items = list(MyModel.objects.filter(pk__in=args[0]))
    continued, count = process_batch(items)
    if not continued:
        context.player.tell(f"Done. Processed {count}.")
```

Rules:
- Pass only `args[0] = list[int]` of remaining PKs — no accumulated counts or errors (those were already told to the player via `tell()` in real time)
- Helper function names must not start with `_` (RestrictedPython blocks them)
- `context.parser` is `None` in continuation mode — use `this.get_verb(name)` as fallback
- Reference implementation: `moo/bootstrap/default_verbs/programmer/at_reload.py`

## `open_editor(obj, initial_content, callback_verb, *args, content_type="text")`

Open a full-screen text editor in the player's SSH terminal.

```python
open_editor(context.player, existing_text, obj.save_verb, content_type="python")
```

- `callback_verb` — Verb invoked with the saved text as `args[0]` followed by `*args`
- `content_type` — `"text"` (default), `"python"`, or `"json"` (controls syntax highlighting)
- Wizard-owned verbs only.

## `open_paginator(obj, content, content_type="text")`

Open a full-screen read-only paginator in the player's SSH terminal.

```python
open_paginator(context.player, long_text, content_type="python")
```

- Wizard-owned verbs only.

## `players()`

Return all player avatar Objects (connected or not).

```python
all_players = players()
```

## `connected_players(within=None)`

Return player avatar Objects whose `last_connected_time` was updated within the given window (default: 5 minutes).

```python
from datetime import timedelta
active = connected_players(within=timedelta(minutes=10))
```

## `set_task_perms(who)`

Context manager. Temporarily set the execution permissions to those of `who`.

```python
with set_task_perms(system):
    privileged_operation()
```

- Wizard-owned verbs only.

## Exceptions

All of these inherit from `UserError`. Any `UserError` (or subclass) raised inside a verb is automatically caught by the task runner and displayed to the player as a bold red message. Verbs do not need to wrap these in `try/except` just to report errors — raising them is the correct pattern.

For example, calling `context.parser.get_dobj()` when the player typed a non-existent object name will raise `NoSuchObjectError("widget")`, and the player will see: `There is no 'widget' here.`

All importable from `moo.sdk`:

| Exception | Message shown to player | When raised |
|-----------|------------------------|-------------|
| `NoSuchObjectError(name)` | `"There is no '<name>' here."` | `lookup()` finds nothing; `get_dobj()` / `get_pobj()` can't resolve |
| `NoSuchVerbError(name)` | `"I don't know how to do that."` | Verb not found on object or its parents |
| `NoSuchPropertyError(name)` | `"There is no '<name>' property defined."` | `get_property()` finds nothing |
| `AmbiguousObjectError(name, matches)` | `"When you say '<name>', do you mean …?"` | `lookup()` finds more than one match |
| `UsageError(message)` | The message string | Convenience for usage/validation errors |
| `QuotaError(message)` | The message string | Quota exceeded during `create()` |

`UsageError` is useful when a verb wants to exit cleanly with a usage message:
```python
from moo.sdk import UsageError

if not context.parser.has_dobj_str():
    raise UsageError("Usage: @create <name>")
```

Any other uncaught exception (not a `UserError`) shows `"An error occurred while executing the command."` to regular players, and a full traceback to wizards.

`NoSuchPropertyError` is also importable directly from `moo.core`:
```python
from moo.core import NoSuchPropertyError
```

## `$string_utils` Verbs

Two utility verbs live on the `$string_utils` object (accessed as `_.string_utils`).

### `rewrap(text)`

Reflows a block of text for terminal display.

```python
result = _.string_utils.rewrap(some_text)
```

- Normalizes line endings (`\r\n`, `\r` → `\n`)
- Collapses whitespace gremlins (tabs, non-breaking spaces) to single spaces
- Collapses runs of multiple spaces
- Splits on paragraph breaks (two or more newlines)
- Within each paragraph, collapses single newlines to spaces, then word-wraps to 80 characters
- Rejoins paragraphs with `\n\n`

`description` properties are passed through `rewrap` automatically before display (see `root_class/description.py`). You only need to call it manually when formatting multi-line text in other contexts.

### `pronoun_sub(text, who=None)`

Substitutes pronoun format codes in `text` using properties of `who` (defaults to `context.player`).

```python
result = _.string_utils.pronoun_sub("%N picks up %t.", actor)
```

| Code | Property | Default | Example |
|------|----------|---------|---------|
| `%%` | — | `%` | — |
| `%s` / `%S` | `who.ps` / `who.psc` | he/she/it | He |
| `%o` / `%O` | `who.po` / `who.poc` | him/her/it | Him |
| `%p` / `%P` | `who.pp` / `who.ppc` | his/her/its | His |
| `%r` / `%R` | `who.pr` / `who.prc` | himself/herself/itself | Himself |
| `%n` / `%N` | `who.name` | — | (capitalized for `%N`) |
| `%d` / `%D` | `dobj.name` (from parser) | unchanged | (capitalized for `%D`) |
| `%i(prep)` / `%I(prep)` | `pobj.name` for `prep` | unchanged | (capitalized for `%I`) |
| `%t` / `%T` | `parser.this.name` | unchanged | (capitalized for `%T`) |
| `%x(prop)` / `%X(prop)` | `who.prop` (any property) | unchanged | (capitalized for `%X`) |

Uppercase codes capitalize the result. Codes that require a parser context (`%d`, `%i`, `%t`) are left unchanged when `context.parser` is `None`.

`_msg` properties on `$furniture`, `$container`, `$thing`, and similar objects use these codes. Override them per-instance to customize flavor text.

## Connection and Movement Hooks

Override these verbs on `$room` or `$player` subclasses for custom behavior.

**Movement** (fired by `object.py` on every `moveto()`; `args[1]` = the moving object):

| Verb | `this` |
|------|--------|
| `$room:enterfunc` | destination room |
| `$room:exitfunc` | source room |

**Connection** (fired by `moo/shell/prompt.py` on SSH session start/end; no args):

| Verb | `this` | Call order |
|------|--------|-----------|
| `$player:confunc` | player | 1st on connect |
| `$room:confunc` | player's room | 2nd on connect |
| `$room:disfunc` | player's room | 1st on disconnect |
| `$player:disfunc` | player | 2nd on disconnect |

`context.player` is the connecting/disconnecting player in all four cases.
`$player:confunc` and `$player:disfunc` are no-op stubs — safe to override.
