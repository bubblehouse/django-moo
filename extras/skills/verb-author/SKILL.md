---
name: verb-author
description: Write and review DjangoMOO verb files. Use when asked to create, modify, or debug verbs in moo/bootstrap/default_verbs/ or for any task involving the `#!moo` shebang syntax, RestrictedPython verb execution, the moo.sdk API, or verb testing.
---

# Verb Author

This skill covers writing verb files for the DjangoMOO project.

## Shebang Syntax

Every verb file must start with a shebang line:

```
#!moo verb name1 [name2 ...] --on $object [--dspec SPEC] [--ispec PREP:SPEC ...]
```

**`name1 [name2 ...]`** — space-separated verb names (aliases). Example: `take get`

**`--on $object`** — the object to attach the verb to, using `$name` syntax to reference a property on the system object (#1). Common targets:
- `$root_class` — all objects
- `$room` — room commands
- `$player` — player commands
- `$thing` — generic thing
- `$exit` — exit objects
- `$container` — container objects

Although there hasn't been a need yet, you could also target arbitrary objects by name, e.g., `--on "magic wand"`. This is a global lookup, so it's important to ensure the name is unique and doesn't cause conflicts.

**`--dspec SPEC`** — direct object specifier:
- omitted — verb will not match if a dobj is typed
- `any` — verb requires a dobj string
- `this` — dobj must resolve to the object the verb is on
- `none` - (uncommon) dobj must not be provided, useful when a verb supports a preposition (e.g., `crawl --ispec under:any`), but not a direct object (e.g., `crawl` to crawl without a target)
- `either` — dobj is optional

**`--ispec PREP:SPEC`** — indirect object specifiers (repeatable). PREP is a preposition from `settings.PREPOSITIONS` (e.g., `in`, `on`, `with`, `at`, `from`, `to`). SPEC is `any`, `this`, or `none`.

Indirect object specifiers can seem like they are optional, but they help the parser distinguish between different prepositions and ensure the correct parsing of commands.

Examples:
```python
#!moo verb accept --on $room
#!moo verb drop --on $thing --dspec this
#!moo verb look inspect --on $room --dspec either --ispec at:any
#!moo verb put give --on $thing --dspec this --ispec on:this in:this
#!moo verb page --on $player --dspec any --ispec with:any
```

## Execution Environment

Every verb file body is compiled as the body of this function — do **not** redeclare it:

```python
def verb(this, passthrough, _, *args, **kwargs):
    ...
```

Injected variables (always available, no import needed):

| Variable | Type | Meaning |
|----------|------|---------|
| `this` | Object | Object where verb was found (last match in dispatch order) |
| `passthrough` | callable | Invoke the verb on parent objects (`super()` equivalent) |
| `_` | Object | System object (#1) |
| `args` | tuple | Positional arguments when called as a method |
| `kwargs` | dict | Keyword arguments when called as a method |
| `verb_name` | str | The specific alias used to invoke this verb |

Include this pylint comment at the top of every verb file:

```python
# pylint: disable=return-outside-function,undefined-variable
```

### Sandbox Restrictions

Allowed imports: `moo.sdk`, `hashlib`, `re`, `datetime`, `time`

Allowed builtins: `dict`, `enumerate`, `getattr`, `hasattr`, `list`, `set`, `sorted`

Verbs cannot: import arbitrary modules, access the filesystem, open network connections, use `__import__`, `exec`, or `eval`.

## Output to Players

| Method | Who sees it | Notes |
|--------|-------------|-------|
| `print(msg)` | Caller only | Direct to initiator's console |
| `obj.tell(msg)` | `obj` | Goes through tell verb chain (gag/paranoia filtering) |
| `write(obj, msg)` | `obj` | Low-level, bypasses filtering; wizard-owned verbs only |

**`return "..."` does NOT display anything.** It merely returns the value to whatever called the verb. Always use `print()` or `write()` (or `obj.tell()`) for user-visible output.

## Object API Quick Reference

```python
# Properties
obj.get_property(name)    # raises NoSuchPropertyError if missing
obj.set_property(name, value)
obj.has_property(name)    # avoid — prefer try/except pattern below

# Prefer this pattern (1 query) over has+get (2 queries):
try:
    value = obj.get_property("key")
except NoSuchPropertyError:
    value = default

# Navigation
obj.location                             # ForeignKey to container
obj.contents.all()                       # direct contents QuerySet
obj.find(name)                           # find contents by name
obj.moveto(destination)                  # move object (triggers accept/enter/exit hooks)
obj.parents.all()                        # ManyToMany parents — always call .all()

# Identity
obj.title()                              # display name
obj.is_player()
obj.is_wizard()
obj.is_connected()

# Verb dispatch
obj.invoke_verb(name, *args)
obj.has_verb(name)

# Room broadcast
room.announce(msg)                       # all occupants except caller
room.announce_all(msg)                   # all occupants including caller
room.announce_all_but(obj, msg)          # all occupants except obj
```

## Performance Rules

1. Assign to a local when a property or method result is used more than once:
   ```python
   title = this.title()   # one query; reuse title below
   print(f"You take {title}.")
   ```

2. Use `try/except NoSuchPropertyError` instead of `has_property` + `get_property`:
   ```python
   try:
       free_entry = dest.get_property("free_entry")
   except NoSuchPropertyError:
       free_entry = False
   ```

3. Pre-fetch `contents.all()` before multiple announce calls:
   ```python
   source_contents = list(source.contents.all())
   dest_contents = list(dest.contents.all())
   source.announce_all_but(thing, msg, source_contents)
   dest.announce_all_but(thing, msg, dest_contents)
   ```

4. Sub-verbs that need the same properties (e.g., source/dest) should accept them as `args[0]`/`args[1]` with a `NoSuchPropertyError` fallback for standalone calls.

## Imports Reference

See [sdk.md](references/sdk.md) for the full `moo.sdk` API.

Common import lines:
```python
from moo.sdk import context
from moo.sdk import context, lookup, create, invoke, write
from moo.sdk import context, NoSuchPropertyError
from moo.sdk import NoSuchObjectError, NoSuchVerbError, NoSuchPropertyError
```

## Annotated Examples

### take.py — `--dspec this` verb

```python
#!moo verb take get --on $thing --dspec this

# pylint: disable=return-outside-function,undefined-variable

from moo.sdk import context

title = this.title()                        # cache — used 3+ times below
if this.location == context.player:
    print(f"You already have {title} in your inventory.")
elif this.moveto(context.player):           # moveto returns True on success
    print(this.take_succeeded_msg(title))
    if msg := this.otake_succeeded_msg(title):
        this.location.announce(msg)         # tell others in the room
else:
    print(this.take_failed_msg(title))
    if msg := this.otake_failed_msg(title):
        this.location.announce(msg)
```

Key points: `--dspec this` means the dobj must resolve to `this`. `context.player` is the initiator.

### look.py — optional dobj with preposition

```python
#!moo verb look inspect --on $room --dspec either --ispec at:any

# pylint: disable=return-outside-function,undefined-variable

from moo.sdk import context

if context.parser.has_pobj_str("in"):
    container = context.parser.get_pobj("in")   # returns Object
else:
    container = None

if context.parser.has_dobj() and container is None:
    obj = context.parser.get_dobj()
elif context.parser.has_dobj_str():
    dobj_str = context.parser.get_dobj_str()
    qs = context.player.find(dobj_str) or context.player.location.find(dobj_str)
    if not qs:
        print(f"There is no '{dobj_str}' here.")
        return
    obj = qs[0]
else:
    obj = context.player.location

obj.look_self()
```

Key points: `has_pobj_str` / `get_pobj_str` — not `…_string`. `get_pobj` returns an Object; `get_pobj_str` returns a raw string.

### exit/move.py — method verb with args

```python
#!moo verb move --on $exit

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

from moo.sdk import context, NoSuchPropertyError

thing = args[0]
source = this.get_property("source")
dest = this.get_property("dest")

try:
    free_entry = dest.get_property("free_entry")
except NoSuchPropertyError:
    free_entry = False

if free_entry:
    accepted = True
else:
    dest.bless_for_entry(context.caller)
    accepted = dest.accept(thing)

source_contents = list(source.contents.all())
dest_contents = list(dest.contents.all())

if accepted:
    thing.tell(this.leave_msg(source, dest))
    source.announce_all_but(thing, this.oleave_msg(source, dest), source_contents)
    thing.moveto(dest)
    thing.tell(this.arrive_msg(source, dest))
    dest.announce_all_but(thing, this.oarrive_msg(source, dest), dest_contents)
else:
    thing.tell(this.nogo_msg(source, dest))
    source.announce_all_but(thing, this.onogo_msg(source, dest), source_contents)
```

Key points: `args[0]` for the first method argument. `NoSuchPropertyError` import for optional property check. Pre-fetch contents once per room.

## Error Handling

`UserError` and all its subclasses (`NoSuchObjectError`, `NoSuchVerbError`, `NoSuchPropertyError`, `UsageError`, `QuotaError`, etc.) are automatically caught by the task runner and displayed to the player as a bold red message. Verbs do not need to catch these to report errors — raising them is the correct and idiomatic pattern.

Letting `get_dobj()` raise `NoSuchObjectError` is intentional: if the player typed a name that doesn't exist, they will see `"There is no 'X' here."` with no extra code in the verb.

Use `UsageError` to signal bad syntax or missing arguments:
```python
from moo.sdk import UsageError

if not context.parser.has_dobj_str():
    raise UsageError(f"Usage: {verb_name} <target>")
```

Only catch `UserError` subclasses when you need different behaviour from the default message:
```python
try:
    target = context.parser.get_dobj()
except NoSuchObjectError:
    print("You'll need to be more specific.")
    return
```

Any uncaught exception that is not a `UserError` shows a generic error to regular players and a full traceback to wizards.

## Time-Aware Continuation

Verbs that iterate over many objects must hand off remaining work before the task time limit hits. Use `context.task_time.remaining` to check how much time is left, and `invoke()` to schedule a continuation task.

```python
TIME_THRESHOLD = 0.5  # hand off when 0.5 s remain

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

# Detect continuation: args[0] is a list of PKs from a prior batch
if args and isinstance(args[0], list):
    items = list(MyModel.objects.filter(pk__in=args[0]))
    continued, count = process_batch(items)
    if not continued:
        context.player.tell(f"Done. Processed {count}.")
else:
    items = list(MyModel.objects.filter(...))
    continued, count = process_batch(items)
    if not continued:
        context.player.tell(f"Done. Processed {count}.")
```

Rules:
- `context.task_time` returns `TaskTime(elapsed, time_limit, remaining)` or `None` (no limit). Always guard: `if tt and tt.remaining is not None`.
- Pass only `args[0] = list[int]` of remaining PKs to the continuation — no accumulated counts or error strings. Progress messages are delivered in real time via `context.player.tell()` as each item is processed.
- Use `context.player.tell()` inside the loop, not `print()`. `tell()` writes immediately; `print()` buffers until the verb returns.
- Materialize querysets to `list()` before the loop so the DB cursor doesn't span the time check.
- `context.parser` is `None` in continuation mode (the verb was invoked by Celery, not the parser). Fall back to `this.get_verb(name)` for the verb reference.
- Helper function names must not start with `_` — RestrictedPython blocks underscore-prefixed names.
- Reference implementation: `moo/bootstrap/default_verbs/programmer/at_reload.py`.

## Pitfalls

- `get_pobj_string()` / `has_pobj_string()` do not exist. Use `get_pobj_str()` / `has_pobj_str()`.
- `if player != this:` breaks on any verb with a dspec. `this` is the last matched object in dispatch order, not the caller. Use `context.player` for the initiator.
- `obj.parents` is a ManyRelatedManager. Always call `.all()` to iterate.
- `has_property(x)` + `get_property(x)` is 2 queries. Use `try: get_property() except NoSuchPropertyError`.
- Verbs on `$player` with `--dspec any`: when dobj and caller both inherit the verb, the dobj wins — `this` = dobj, `context.player` = caller.

## Further Reference

- [dispatch.md](references/dispatch.md) — verb search order, `this` vs `context.player` in depth
- [parser-api.md](references/parser-api.md) — complete Parser method table
- [sdk.md](references/sdk.md) — full `moo.sdk` function reference
- [testing.md](references/testing.md) — test patterns, fixtures, and examples
